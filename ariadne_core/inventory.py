"""Open-world inventory for unresolved repositories, Git branches, names and artifacts.

Inventory is retention, not classification. An observed resource may remain unmapped
to any project indefinitely without being discarded or promoted into a project FORK.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .store import encoded, event, identity

ITEM_TYPES={"NAMED_LINE","REPOSITORY","GIT_BRANCH","ARTIFACT","OTHER"}
ITEM_STATUSES={"OBSERVED","UNVERIFIED","CLASSIFICATION_PENDING","NO_MATCH","RETIRED"}

SCHEMA="""
CREATE TABLE IF NOT EXISTS federation_inventory (
 inventory_id TEXT PRIMARY KEY,
 item_type TEXT NOT NULL,
 locator TEXT,
 label TEXT NOT NULL,
 status TEXT NOT NULL,
 project_id TEXT REFERENCES federation_projects(project_id),
 parent_inventory_id TEXT REFERENCES federation_inventory(inventory_id),
 detail TEXT NOT NULL DEFAULT '{}',
 observed_at TEXT NOT NULL,
 UNIQUE(item_type,locator,label,project_id,parent_inventory_id)
);
CREATE INDEX IF NOT EXISTS federation_inventory_project ON federation_inventory(project_id,item_type,status);
CREATE INDEX IF NOT EXISTS federation_inventory_parent ON federation_inventory(parent_inventory_id,item_type);
"""


def _now(): return datetime.now(timezone.utc).isoformat()

def install(con): con.executescript(SCHEMA)

def record_item(con,item_type,label,locator=None,status="OBSERVED",project_id=None,parent_inventory_id=None,detail=None):
    if item_type not in ITEM_TYPES: raise ValueError(f"unsupported inventory type: {item_type}")
    if status not in ITEM_STATUSES: raise ValueError(f"unsupported inventory status: {status}")
    if project_id and con.execute("SELECT 1 FROM federation_projects WHERE project_id=?",(project_id,)).fetchone() is None:
        raise ValueError("unknown project")
    if parent_inventory_id and con.execute("SELECT 1 FROM federation_inventory WHERE inventory_id=?",(parent_inventory_id,)).fetchone() is None:
        raise ValueError("unknown parent inventory item")
    label=str(label).strip()
    if not label: raise ValueError("inventory label is required")
    locator=str(locator).strip() if locator else None
    iid=identity("INV",item_type,locator,label,project_id,parent_inventory_id)
    con.execute("""INSERT OR IGNORE INTO federation_inventory
        (inventory_id,item_type,locator,label,status,project_id,parent_inventory_id,detail,observed_at)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (iid,item_type,locator,label,status,project_id,parent_inventory_id,encoded(detail or {}),_now()))
    event(con,"FEDERATION_INVENTORY",iid,{"item_type":item_type,"label":label,"locator":locator,
          "status":status,"project_id":project_id,"parent_inventory_id":parent_inventory_id})
    return iid


def record_repository(con,repository,project_id=None,status="OBSERVED",detail=None):
    return record_item(con,"REPOSITORY",repository,repository,status,project_id,None,detail)


def record_git_branch(con,repository,branch,project_id=None,status="OBSERVED",repository_inventory_id=None,commit_sha=None,detail=None):
    data=dict(detail or {})
    if commit_sha: data["commit_sha"]=commit_sha
    return record_item(con,"GIT_BRANCH",branch,f"{repository}#{branch}",status,project_id,repository_inventory_id,data)


def unclassified(con):
    """Return retained items not yet mapped to a project, without deleting/demoting them."""
    return [dict(r) for r in con.execute("""SELECT * FROM federation_inventory
        WHERE project_id IS NULL AND status!='RETIRED' ORDER BY item_type,label""")]
