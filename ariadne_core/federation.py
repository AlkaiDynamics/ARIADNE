"""Project-agnostic federation primitives.

Repository identity, Git branch identity, project identity, and durable epistemic
fork identity are deliberately separate. The registry is open-world: discovering a
name creates an inventory record without requiring an immediate classification.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .store import encoded, event, identity

PROJECT_STATUSES = {"REGISTERED","REGISTERED_UNSPECIFIED","CLASSIFICATION_PENDING","BANKED","RETIRED"}
FORK_TYPES = {"EPISTEMIC","CORPUS","MODEL","CONTROL","APPLICATION","IMPLEMENTATION","PRESENTATION","EXPERIMENT","UNRESOLVED"}
FORK_STATUSES = {"ACTIVE","REJOINED","PARTIAL_REJOIN","SUPERSEDED","REFUTED","BANKED","CONTROL","DIVERGED"}
VALIDATION_REGIMES = {"FORMAL","HISTORICAL_TEXTUAL","EMPIRICAL","ENGINEERING","NORMATIVE"}
HANDOFF_STATUSES = {"PENDING","ACCEPTED","PARTIAL","DEFERRED","REJECTED"}
REPOSITORY_OBSERVATIONS = {"OBSERVED","PARTIALLY_OBSERVED","UNVERIFIED","NO_MATCH_IN_CURRENT_CENSUS"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS federation_projects (
 project_id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'UNRESOLVED',
 status TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS federation_project_aliases (
 project_id TEXT NOT NULL REFERENCES federation_projects(project_id), alias TEXT NOT NULL,
 PRIMARY KEY(project_id,alias));
CREATE TABLE IF NOT EXISTS federation_repository_observations (
 observation_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES federation_projects(project_id),
 repository TEXT, observation_status TEXT NOT NULL, observed_at TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS federation_repo_project ON federation_repository_observations(project_id,observation_status);
CREATE TABLE IF NOT EXISTS federation_project_relations (
 relation_id TEXT PRIMARY KEY, src_project TEXT NOT NULL REFERENCES federation_projects(project_id),
 dst_project TEXT NOT NULL REFERENCES federation_projects(project_id), relation TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PROPOSED', evidence TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_forks (
 fork_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES federation_projects(project_id),
 focus_id TEXT NOT NULL DEFAULT 'UNSCOPED', fork_type TEXT NOT NULL,
 parent_fork TEXT REFERENCES project_forks(fork_id), parent_snapshot TEXT,
 forced_focus TEXT NOT NULL DEFAULT '', reason_for_fork TEXT NOT NULL DEFAULT '',
 inherited_invariants TEXT NOT NULL DEFAULT '[]', frozen_inputs TEXT NOT NULL DEFAULT '[]',
 allowed_changes TEXT NOT NULL DEFAULT '[]', forbidden_changes TEXT NOT NULL DEFAULT '[]',
 evidence_visibility TEXT NOT NULL DEFAULT '{}', leakage_policy TEXT NOT NULL DEFAULT '{}',
 hypotheses TEXT NOT NULL DEFAULT '[]', predictions TEXT NOT NULL DEFAULT '[]', controls TEXT NOT NULL DEFAULT '[]',
 return_conditions TEXT NOT NULL DEFAULT '[]', merge_policy TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL,
 decision_records TEXT NOT NULL DEFAULT '[]', checkpoint_stream TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS project_fork_project ON project_forks(project_id,focus_id,status);
CREATE TABLE IF NOT EXISTS validation_records (
 validation_id TEXT PRIMARY KEY, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
 regime TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}', decision_id TEXT,
 created_at TEXT NOT NULL, UNIQUE(subject_type,subject_id,regime,status,decision_id));
CREATE INDEX IF NOT EXISTS validation_subject ON validation_records(subject_type,subject_id,regime);
CREATE TABLE IF NOT EXISTS federation_handoffs (
 handoff_id TEXT PRIMARY KEY, from_project TEXT NOT NULL REFERENCES federation_projects(project_id),
 to_project TEXT NOT NULL REFERENCES federation_projects(project_id), source_snapshot TEXT NOT NULL,
 epistemic_zones TEXT NOT NULL DEFAULT '[]', validation_regimes TEXT NOT NULL DEFAULT '[]',
 transformation_applied TEXT NOT NULL DEFAULT '{}', assumptions TEXT NOT NULL DEFAULT '[]',
 known_failures TEXT NOT NULL DEFAULT '[]', unresolved_items TEXT NOT NULL DEFAULT '[]',
 protected_invariants TEXT NOT NULL DEFAULT '[]', accepted_status TEXT NOT NULL,
 decision_authority TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS federation_handoff_payloads (
 handoff_id TEXT NOT NULL REFERENCES federation_handoffs(handoff_id), record_id TEXT NOT NULL,
 source_identity TEXT, PRIMARY KEY(handoff_id,record_id));
"""


def _now(): return datetime.now(timezone.utc).isoformat()

def install(con): con.executescript(SCHEMA)

def _check(value, allowed, label):
    if value not in allowed: raise ValueError(f"unsupported {label}: {value}")


def register_project(con, project_id, name=None, role="UNRESOLVED", status="CLASSIFICATION_PENDING", aliases=None, metadata=None):
    """Inventory a project without forcing a parent, repository, or semantic class."""
    _check(status,PROJECT_STATUSES,"project status")
    project_id=str(project_id).strip()
    if not project_id: raise ValueError("project_id is required")
    name=str(name or project_id).strip();ts=_now()
    existing=con.execute("SELECT * FROM federation_projects WHERE project_id=?",(project_id,)).fetchone()
    if existing is None:
        con.execute("INSERT INTO federation_projects VALUES(?,?,?,?,?,?,?)",
                    (project_id,name,role,status,encoded(metadata or {}),ts,ts))
        event(con,"FEDERATION_PROJECT_REGISTERED",project_id,{"name":name,"role":role,"status":status})
    else:
        prior=json.loads(existing["metadata"])
        con.execute("UPDATE federation_projects SET name=?,role=?,status=?,metadata=?,updated_at=? WHERE project_id=?",
                    (name,role,status,encoded(prior if metadata is None else metadata),ts,project_id))
        event(con,"FEDERATION_PROJECT_UPDATED",project_id,{"name":name,"role":role,"status":status})
    for alias in aliases or []:
        alias=str(alias).strip()
        if alias: con.execute("INSERT OR IGNORE INTO federation_project_aliases VALUES(?,?)",(project_id,alias))
    return project_id


def observe_repository(con, project_id, repository=None, status="OBSERVED", detail=None):
    """Record repository evidence without equating repository and project identity."""
    _check(status,REPOSITORY_OBSERVATIONS,"repository observation")
    if con.execute("SELECT 1 FROM federation_projects WHERE project_id=?",(project_id,)).fetchone() is None:
        raise ValueError("register project before repository observation")
    repository=str(repository).strip() if repository else None
    oid=identity("REPOOBS",project_id,repository,status,detail or {})
    con.execute("INSERT OR IGNORE INTO federation_repository_observations VALUES(?,?,?,?,?,?)",
                (oid,project_id,repository,status,_now(),encoded(detail or {})))
    event(con,"FEDERATION_REPOSITORY_OBSERVED",oid,{"project_id":project_id,"repository":repository,"status":status})
    return oid


def relate_projects(con, src_project, dst_project, relation, status="PROPOSED", evidence=None):
    """Relations are explicit; unresolved projects receive no inferred hierarchy."""
    if src_project==dst_project: raise ValueError("project relation requires distinct projects")
    for pid in (src_project,dst_project):
        if con.execute("SELECT 1 FROM federation_projects WHERE project_id=?",(pid,)).fetchone() is None:
            raise ValueError(f"unknown project: {pid}")
    rid=identity("PROJREL",src_project,dst_project,relation,status,evidence or {})
    con.execute("INSERT OR IGNORE INTO federation_project_relations VALUES(?,?,?,?,?,?,?)",
                (rid,src_project,dst_project,relation,status,encoded(evidence or {}),_now()))
    event(con,"FEDERATION_PROJECT_RELATION",rid,{"src":src_project,"dst":dst_project,"relation":relation,"status":status})
    return rid


def create_fork(con, project_id, fork_type="UNRESOLVED", focus_id="UNSCOPED", parent_fork=None,
                parent_snapshot=None, forced_focus="", reason_for_fork="", inherited_invariants=None,
                frozen_inputs=None, allowed_changes=None, forbidden_changes=None, evidence_visibility=None,
                leakage_policy=None, hypotheses=None, predictions=None, controls=None, return_conditions=None,
                merge_policy=None, status="ACTIVE", decision_records=None, checkpoint_stream=None, fork_id=None):
    _check(fork_type,FORK_TYPES,"fork type");_check(status,FORK_STATUSES,"fork status")
    if con.execute("SELECT 1 FROM federation_projects WHERE project_id=?",(project_id,)).fetchone() is None:
        raise ValueError("register project before creating a fork")
    if parent_fork and con.execute("SELECT 1 FROM project_forks WHERE fork_id=?",(parent_fork,)).fetchone() is None:
        raise ValueError("unknown parent fork")
    ts=_now();fid=fork_id or identity("FORK",project_id,focus_id,parent_fork,parent_snapshot,fork_type,forced_focus,reason_for_fork,ts)
    row=dict(fork_id=fid,project_id=project_id,focus_id=focus_id,fork_type=fork_type,parent_fork=parent_fork,
             parent_snapshot=parent_snapshot,forced_focus=forced_focus,reason_for_fork=reason_for_fork,
             inherited_invariants=encoded(inherited_invariants or []),frozen_inputs=encoded(frozen_inputs or []),
             allowed_changes=encoded(allowed_changes or []),forbidden_changes=encoded(forbidden_changes or []),
             evidence_visibility=encoded(evidence_visibility or {}),leakage_policy=encoded(leakage_policy or {}),
             hypotheses=encoded(hypotheses or []),predictions=encoded(predictions or []),controls=encoded(controls or []),
             return_conditions=encoded(return_conditions or []),merge_policy=encoded(merge_policy or {}),status=status,
             decision_records=encoded(decision_records or []),checkpoint_stream=checkpoint_stream,created_at=ts,updated_at=ts)
    con.execute("""INSERT INTO project_forks(
        fork_id,project_id,focus_id,fork_type,parent_fork,parent_snapshot,forced_focus,reason_for_fork,
        inherited_invariants,frozen_inputs,allowed_changes,forbidden_changes,evidence_visibility,leakage_policy,
        hypotheses,predictions,controls,return_conditions,merge_policy,status,decision_records,checkpoint_stream,
        created_at,updated_at)
        VALUES(:fork_id,:project_id,:focus_id,:fork_type,:parent_fork,:parent_snapshot,:forced_focus,:reason_for_fork,
        :inherited_invariants,:frozen_inputs,:allowed_changes,:forbidden_changes,:evidence_visibility,:leakage_policy,
        :hypotheses,:predictions,:controls,:return_conditions,:merge_policy,:status,:decision_records,:checkpoint_stream,
        :created_at,:updated_at)""",row)
    event(con,"FEDERATION_FORK_CREATED",fid,{"project_id":project_id,"focus_id":focus_id,"fork_type":fork_type,
          "parent_fork":parent_fork,"parent_snapshot":parent_snapshot,"status":status})
    return fid


def set_fork_status(con, fork_id, status, decision_record=None):
    _check(status,FORK_STATUSES,"fork status")
    row=con.execute("SELECT decision_records FROM project_forks WHERE fork_id=?",(fork_id,)).fetchone()
    if row is None: raise ValueError("unknown fork")
    decisions=json.loads(row[0])
    if decision_record is not None: decisions.append(decision_record)
    con.execute("UPDATE project_forks SET status=?,decision_records=?,updated_at=? WHERE fork_id=?",
                (status,encoded(decisions),_now(),fork_id))
    event(con,"FEDERATION_FORK_STATUS",fork_id,{"status":status,"decision_record":decision_record})


def record_validation(con, subject_type, subject_id, regime, status, detail=None, decision_id=None):
    _check(regime,VALIDATION_REGIMES,"validation regime")
    vid=identity("VAL",subject_type,subject_id,regime,status,decision_id,detail or {})
    con.execute("INSERT OR IGNORE INTO validation_records VALUES(?,?,?,?,?,?,?,?)",
                (vid,subject_type,subject_id,regime,status,encoded(detail or {}),decision_id,_now()))
    event(con,"VALIDATION_RECORDED",vid,{"subject_type":subject_type,"subject_id":subject_id,"regime":regime,"status":status})
    return vid


def create_handoff(con, from_project, to_project, source_snapshot, payload_record_ids, epistemic_zones=None,
                   validation_regimes=None, transformation_applied=None, assumptions=None, known_failures=None,
                   unresolved_items=None, protected_invariants=None, accepted_status="PENDING", decision_authority="",
                   source_identities=None):
    _check(accepted_status,HANDOFF_STATUSES,"handoff status")
    for pid in (from_project,to_project):
        if con.execute("SELECT 1 FROM federation_projects WHERE project_id=?",(pid,)).fetchone() is None:
            raise ValueError(f"unknown project: {pid}")
    if from_project==to_project: raise ValueError("handoff requires distinct projects")
    payload=list(dict.fromkeys(str(x) for x in payload_record_ids if str(x)))
    if not payload: raise ValueError("handoff requires at least one payload record")
    hid=identity("HANDOFF",from_project,to_project,source_snapshot,payload,_now())
    con.execute("INSERT INTO federation_handoffs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
        hid,from_project,to_project,source_snapshot,encoded(epistemic_zones or []),encoded(validation_regimes or []),
        encoded(transformation_applied or {}),encoded(assumptions or []),encoded(known_failures or []),
        encoded(unresolved_items or []),encoded(protected_invariants or []),accepted_status,decision_authority,_now()))
    identities=source_identities or {}
    con.executemany("INSERT INTO federation_handoff_payloads VALUES(?,?,?)",[(hid,r,identities.get(r)) for r in payload])
    event(con,"FEDERATION_HANDOFF_CREATED",hid,{"from_project":from_project,"to_project":to_project,
          "source_snapshot":source_snapshot,"payload_count":len(payload),"accepted_status":accepted_status})
    return hid
