"""Every committed row transition is versioned; snapshots are recovery artifacts.

The hash chains detect accidental alteration. They are not signatures against an
attacker who controls both database and backups. Never prune research history.
"""
import hashlib
import json
import sqlite3
from pathlib import Path
from .store import encoded, event

EXCLUDED = {'state_versions', 'sqlite_sequence'}


def setup_hash(con):
    con.create_function('ariadne_sha256',1,lambda x:hashlib.sha256(x.encode()).hexdigest(),deterministic=True)
    con.execute('PRAGMA recursive_triggers=ON')


def install_history(con):
    setup_hash(con)
    con.executescript('''
    CREATE TABLE IF NOT EXISTS state_versions (
      revision INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT NOT NULL,
      operation TEXT NOT NULL, old_row TEXT, new_row TEXT,
      previous_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
    CREATE TRIGGER IF NOT EXISTS versions_no_update BEFORE UPDATE ON state_versions
      BEGIN SELECT RAISE(ABORT,'state history is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS versions_no_delete BEFORE DELETE ON state_versions
      BEGIN SELECT RAISE(ABORT,'state history is append-only'); END;
    ''')
    # FTS is a reproducible index over passages; do not duplicate shadow tables.
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
              if r[0] not in EXCLUDED and not r[0].startswith(('sqlite_','passage_fts'))]
    for table in tables:
        columns = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
        def row(alias):
            return 'json_object('+','.join(f"'{c}',{alias}.\"{c}\"" for c in columns)+')'
        exists = con.execute('SELECT 1 FROM sqlite_master WHERE type=\'trigger\' AND name=?',(f'version_{table}_insert',)).fetchone()
        if not exists:
            for r in con.execute(f'SELECT * FROM "{table}"').fetchall():
                append_baseline(con,table,dict(r))
        for op in ('INSERT','UPDATE','DELETE'):
            old = row('OLD') if op != 'INSERT' else 'NULL'
            new = row('NEW') if op != 'DELETE' else 'NULL'
            prior = "COALESCE((SELECT row_hash FROM state_versions ORDER BY revision DESC LIMIT 1),'"+'0'*64+"')"
            payload = f"json_array('{table}','{op}',{old},{new},{prior})"
            # OLD/NEW JSON stored as strings; hash uses JSON-typed objects. Verify with json().
            con.execute(f'''CREATE TRIGGER IF NOT EXISTS "version_{table}_{op.lower()}" AFTER {op} ON "{table}"
            BEGIN INSERT INTO state_versions(table_name,operation,old_row,new_row,previous_hash,row_hash)
              VALUES('{table}','{op}',{old},{new},{prior},ariadne_sha256({payload})); END''')


def append_baseline(con,table,row):
    new = encoded(row)
    previous = con.execute('SELECT row_hash FROM state_versions ORDER BY revision DESC LIMIT 1').fetchone()
    previous = previous[0] if previous else '0'*64
    # Let SQLite serialize identically to its trigger implementation.
    digest = con.execute("SELECT ariadne_sha256(json_array(?,'BASELINE',NULL,json(?),?))",(table,new,previous)).fetchone()[0]
    con.execute("INSERT INTO state_versions(table_name,operation,new_row,previous_hash,row_hash) VALUES(?,'BASELINE',?,?,?)",(table,new,previous,digest))


def verify_history(con):
    setup_hash(con)
    previous = '0'*64
    for r in con.execute('SELECT *,ariadne_sha256(json_array(table_name,operation,json(old_row),json(new_row),previous_hash)) expected FROM state_versions ORDER BY revision'):
        if r['previous_hash'] != previous or r['expected'] != r['row_hash']:
            return False
        previous = r['row_hash']
    return True


def state_at(con, revision):
    """Reconstruct logical table rows at any historical transition, without mutation."""
    tables = {}
    for r in con.execute('SELECT * FROM state_versions WHERE revision<=? ORDER BY revision',(revision,)):
        rows = tables.setdefault(r['table_name'],[])
        old,new = json.loads(r['old_row']) if r['old_row'] else None,json.loads(r['new_row']) if r['new_row'] else None
        if old is not None:
            if old not in rows:
                raise ValueError(f"Broken replay at state revision {r['revision']}")
            rows.remove(old)
        if new is not None:
            rows.append(new)
    return tables


def snapshot(con,root):
    """SQLite online backup, integrity check, content hash and immutable manifest."""
    con.commit()
    root = Path(root)
    directory = root/'artifacts/snapshots'
    directory.mkdir(parents=True,exist_ok=True)
    head = con.execute('SELECT revision,row_hash FROM state_versions ORDER BY revision DESC LIMIT 1').fetchone()
    path = directory/f'state-{head[0]:012d}-{head[1][:12]}.sqlite'
    if path.exists():
        return path
    temporary = path.with_suffix('.tmp')
    with sqlite3.connect(temporary) as dest:
        con.backup(dest)
        if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Snapshot integrity check failed')
    temporary.replace(path)
    manifest = dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    state_revision=head[0],state_hash=head[1],
                    schema=[dict(r) for r in con.execute('SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name')])
    path.with_suffix('.json').write_text(encoded(manifest),encoding='utf-8')
    return path


def recover(snapshot_path,target):
    """Restore to a NEW file; existing research history can never be overwritten."""
    source,target = Path(snapshot_path),Path(target)
    if target.exists():
        raise ValueError('Recovery requires a new target database path')
    manifest = json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('Snapshot checksum mismatch')
    with sqlite3.connect(source) as src:
        src.row_factory=sqlite3.Row
        if not verify_history(src) or src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Snapshot verification failed')
        target.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(target) as dst:
            src.backup(dst)
    return target
