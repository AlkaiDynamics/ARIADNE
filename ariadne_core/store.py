"""Additive v0 migration, immutable derivations and hash-chained processing events."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from . import VERSION


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def identity(prefix, *parts):
    return prefix + '-' + hashlib.sha256(encoded(parts).encode()).hexdigest()[:24]


SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_events (
 seq INTEGER PRIMARY KEY, stage TEXT NOT NULL, subject TEXT NOT NULL,
 payload TEXT NOT NULL, version TEXT NOT NULL, created TEXT NOT NULL,
 previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS immutable_pipeline_update BEFORE UPDATE ON pipeline_events
 BEGIN SELECT RAISE(ABORT, 'pipeline events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS immutable_pipeline_delete BEFORE DELETE ON pipeline_events
 BEGIN SELECT RAISE(ABORT, 'pipeline events are append-only'); END;
CREATE TABLE IF NOT EXISTS pipeline_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS implementation_versions (
 implementation_id TEXT PRIMARY KEY, files_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lens_runs (
 run_id TEXT PRIMARY KEY, lens TEXT NOT NULL, implementation_id TEXT NOT NULL,
 corpus_revision TEXT NOT NULL, config_hash TEXT NOT NULL,
 input_state_revision INTEGER NOT NULL, parameters TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('COMPLETED','DISABLED','FAILED')),
 detail TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS lens_runs_no_update BEFORE UPDATE ON lens_runs
 BEGIN SELECT RAISE(ABORT,'lens runs are append-only'); END;
CREATE TRIGGER IF NOT EXISTS lens_runs_no_delete BEFORE DELETE ON lens_runs
 BEGIN SELECT RAISE(ABORT,'lens runs are append-only'); END;
CREATE TABLE IF NOT EXISTS scale_patterns (
 pattern_id TEXT PRIMARY KEY, level INTEGER NOT NULL, signature TEXT NOT NULL,
 members TEXT NOT NULL, source_count INTEGER NOT NULL, interpretation TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_profiles (
 source_id TEXT PRIMARY KEY REFERENCES sources(source_id), text TEXT NOT NULL,
 family TEXT, tradition TEXT, language TEXT, witness_class TEXT, metadata TEXT NOT NULL,
 compiled_version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_lanes (
 source_id TEXT PRIMARY KEY REFERENCES sources(source_id),
 lane TEXT NOT NULL CHECK(lane IN ('G0','E0')), reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS acquisition_jobs (
 job_id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, discovered_from TEXT NOT NULL,
 depth INTEGER NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt REAL NOT NULL DEFAULT 0, source_id TEXT REFERENCES sources(source_id),
 detail TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS acquisition_links (
 parent_id TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES acquisition_jobs(job_id),
 relation TEXT NOT NULL, PRIMARY KEY(parent_id,job_id,relation));
CREATE TABLE IF NOT EXISTS chat_messages (
 message_id TEXT PRIMARY KEY, stream TEXT NOT NULL, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_checkpoints (
 checkpoint_id TEXT PRIMARY KEY, stream TEXT NOT NULL, message_ids TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES sources(source_id));
CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(passage_id UNINDEXED, text);
CREATE TABLE IF NOT EXISTS passages (
 passage_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
 locator TEXT NOT NULL, text TEXT NOT NULL, UNIQUE(source_id, locator));
CREATE TABLE IF NOT EXISTS gram_index (
 gram TEXT NOT NULL, passage_id TEXT NOT NULL REFERENCES passages(passage_id),
 PRIMARY KEY(gram, passage_id));
CREATE TABLE IF NOT EXISTS findings (
 finding_id TEXT PRIMARY KEY, passage_id TEXT NOT NULL REFERENCES passages(passage_id),
 kind TEXT NOT NULL, signature TEXT, address TEXT, data TEXT NOT NULL,
 provenance_class TEXT NOT NULL DEFAULT 'MACHINE_PREDICTION'
 CHECK(provenance_class='MACHINE_PREDICTION'),
 cell TEXT NOT NULL, version TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS finding_signature ON findings(signature);
CREATE INDEX IF NOT EXISTS finding_address ON findings(address);
CREATE VIEW IF NOT EXISTS discovery_findings AS SELECT f.* FROM findings f
 JOIN passages p USING(passage_id) JOIN source_profiles s USING(source_id)
 WHERE f.version=s.compiled_version;
DROP VIEW IF EXISTS active_findings;
CREATE VIEW active_findings AS SELECT f.* FROM discovery_findings f
 JOIN passages p USING(passage_id) LEFT JOIN source_lanes l USING(source_id)
 WHERE COALESCE(l.lane,'E0')='E0';
CREATE TABLE IF NOT EXISTS graph_edges (
 edge_id TEXT PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL,
 relation TEXT NOT NULL, evidence TEXT NOT NULL, version TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS graph_src ON graph_edges(src, relation);
CREATE INDEX IF NOT EXISTS graph_dst ON graph_edges(dst, relation);
CREATE TABLE IF NOT EXISTS proposals (
 proposal_id TEXT PRIMARY KEY, left_id TEXT NOT NULL REFERENCES findings(finding_id),
 right_id TEXT NOT NULL REFERENCES findings(finding_id), kind TEXT NOT NULL,
 data TEXT NOT NULL, provenance_class TEXT NOT NULL DEFAULT 'MACHINE_PREDICTION'
 CHECK(provenance_class='MACHINE_PREDICTION'), version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS challenges (
 challenge_id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES proposals(proposal_id),
 checks TEXT NOT NULL, verdict TEXT NOT NULL, version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS branches (
 branch_id TEXT PRIMARY KEY, query TEXT NOT NULL, direction TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('OPEN','BANKED','PROTECTED','DEFERRED')),
 depth INTEGER NOT NULL, protected INTEGER NOT NULL, diagnostic REAL NOT NULL,
 torch REAL NOT NULL, trials INTEGER NOT NULL DEFAULT 0,
 reward REAL NOT NULL DEFAULT 0, stale INTEGER NOT NULL DEFAULT 0,
 last_revision TEXT, metrics TEXT NOT NULL DEFAULT '{}', reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS branch_origins (
 branch_id TEXT NOT NULL REFERENCES branches(branch_id),
 finding_id TEXT NOT NULL REFERENCES findings(finding_id),
 parent_id TEXT NOT NULL, PRIMARY KEY(branch_id, finding_id, parent_id));
CREATE TABLE IF NOT EXISTS branch_observations (
 branch_id TEXT NOT NULL REFERENCES branches(branch_id), revision TEXT NOT NULL,
 passage_id TEXT NOT NULL REFERENCES passages(passage_id),
 PRIMARY KEY(branch_id, revision, passage_id));
CREATE TABLE IF NOT EXISTS query_runs (
 run_id TEXT PRIMARY KEY, branch_id TEXT NOT NULL REFERENCES branches(branch_id),
 revision TEXT NOT NULL, result TEXT NOT NULL, version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rule_proposals (
 rule_id TEXT PRIMARY KEY, premises TEXT NOT NULL, expression TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'EXPERIMENTAL', version TEXT NOT NULL);
"""


def migrate(con):
    con.executescript(SCHEMA)
    from .federation import install as install_federation
    install_federation(con)
    from .inventory import install as install_inventory
    install_inventory(con)
    from .history import install_history
    install_history(con)
    con.execute("INSERT OR IGNORE INTO pipeline_state VALUES('schema','1')")


def event(con, stage, subject, payload):
    prior = con.execute('SELECT event_hash FROM pipeline_events ORDER BY seq DESC LIMIT 1').fetchone()
    previous = prior[0] if prior else '0'*64
    created = datetime.now(timezone.utc).isoformat()
    body = [stage, subject, encoded(payload), VERSION, created, previous]
    digest = hashlib.sha256(encoded(body).encode()).hexdigest()
    con.execute('INSERT INTO pipeline_events(stage,subject,payload,version,created,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)', (*body, digest))


def verify_events(con):
    previous = '0'*64
    for row in con.execute('SELECT * FROM pipeline_events ORDER BY seq'):
        body = [row[k] for k in ('stage','subject','payload','version','created','previous_hash')]
        if row['previous_hash'] != previous or hashlib.sha256(encoded(body).encode()).hexdigest() != row['event_hash']:
            return False
        previous = row['event_hash']
    return True