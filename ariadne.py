#!/usr/bin/env python3
"""ARIADNE v0 — feed-first evidence custody and research navigation.

Standard-library only by design.

Core contract:
- Preserve sources before interpretation.
- Never silently collapse competing claims.
- Treat machine findings as candidates, not truths.
- Keep residuals/outliers as first-class records.
- Revisit banked research torches when new material arrives.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import sqlite3
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "db"
DB_PATH = DB_DIR / "ariadne.sqlite"
INBOX_DIR = ROOT / "inbox"
CUSTODY_DIR = ROOT / "custody"
ARTIFACTS_DIR = ROOT / "artifacts"
CONFIG_DIR = ROOT / "config"
TORCH_CONFIG = CONFIG_DIR / "torches.json"
REPORT_PATH = ARTIFACTS_DIR / "latest_report.html"

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".html", ".htm", ".xml", ".yaml", ".yml"}

RESIDUAL_WORDS = {
    "missing": "MISSING",
    "omitted": "OMITTED",
    "omission": "OMITTED",
    "lacuna": "LACUNA",
    "withheld": "WITHHELD",
    "duplicate": "DUPLICATE",
    "duplicated": "DUPLICATE",
    "unpaired": "UNPAIRED",
    "untranslated": "UNTRANSLATED",
    "unknown": "UNKNOWN",
    "failed control": "FAILED_CONTROL",
}

SCHEMA = r"""
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    original_path TEXT NOT NULL,
    custody_path TEXT NOT NULL,
    extension TEXT,
    byte_size INTEGER NOT NULL,
    text_extracted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingest_events (
    event_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assertions (
    assertion_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    kind TEXT NOT NULL,
    statement TEXT NOT NULL,
    provenance_class TEXT NOT NULL,
    locator TEXT,
    extraction_method TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discrepancies (
    discrepancy_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    left_value TEXT NOT NULL,
    right_value TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    discrepancy_class TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
    provenance_class TEXT NOT NULL DEFAULT 'MACHINE_PREDICTION',
    locator TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transforms (
    transform_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    from_value TEXT NOT NULL,
    to_value TEXT NOT NULL,
    operator TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    provenance_class TEXT NOT NULL DEFAULT 'MACHINE_PREDICTION',
    locator TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS residuals (
    residual_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    residual_type TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    locator TEXT,
    provenance_class TEXT NOT NULL DEFAULT 'MACHINE_PREDICTION',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS torches (
    torch_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('BURNING','BANKED','REIGNITED')),
    why_red TEXT,
    return_trigger TEXT,
    any_terms_json TEXT NOT NULL,
    all_terms_json TEXT NOT NULL,
    min_hits INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'config',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS torch_hits (
    hit_id TEXT PRIMARY KEY,
    torch_id TEXT NOT NULL REFERENCES torches(torch_id),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    matched_terms_json TEXT NOT NULL,
    score INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(torch_id, source_id)
);
CREATE TABLE IF NOT EXISTS investigation_queue (
    queue_id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES sources(source_id),
    torch_id TEXT REFERENCES torches(torch_id),
    direction TEXT NOT NULL CHECK(direction IN ('DOWN','SIDEWAYS','ORTHOGONAL','UP','GENERAL')),
    title TEXT NOT NULL,
    reason TEXT NOT NULL,
    epistemic_support TEXT NOT NULL DEFAULT 'LOW',
    diagnostic_value TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assertions_source ON assertions(source_id);
CREATE INDEX IF NOT EXISTS idx_discrepancies_source ON discrepancies(source_id);
CREATE INDEX IF NOT EXISTS idx_transforms_source ON transforms(source_id);
CREATE INDEX IF NOT EXISTS idx_residuals_source ON residuals(source_id);
CREATE INDEX IF NOT EXISTS idx_torch_hits_source ON torch_hits(source_id);
CREATE INDEX IF NOT EXISTS idx_queue_status ON investigation_queue(status);
"""

DEFAULT_TORCHES = [
    {"torch_id":"TORCH-70-LANGUAGES","title":"70 target languages","state":"BANKED","why_red":"Resolve which language/nation members move across 70/72 witnesses and what moves with them.","return_trigger":"Any new 70/72, language, nation, Babel, court, translator, or genealogy evidence.","any_terms":["70 languages","seventy languages","72 languages","seventy-two languages","babel","interpreter","translator"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-SORCERY-TARGETS","title":"Sorcery targets and operators","state":"BANKED","why_red":"Classify what is acted upon and by which operators; compare later angel/demon/decan functional grids.","return_trigger":"Any sorcery, magic, binding, invocation, healing, divination, weather, disease, name, spirit, speech, or boundary evidence.","any_terms":["sorcery","magic","bind","binding","invoke","invocation","divination","spell","conjuration","spirit","weather","disease"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-JUDAH","title":"House of Judah / Aristeas fourth group","state":"BANKED","why_red":"Protected bright-red thread: fourth-group 5/6 damage and divergent repair may alter the larger transmission architecture.","return_trigger":"New Judah, fourth tribe/group, Aristeas, Zechariah, Hilkiah/Chelkias, Chabrias, Jesus lineage, or 5/6 evidence.","any_terms":["judah","fourth tribe","fourth group","aristeas","zechariah","hilkiah","chelkias","chabrias","5/6","five of six"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-36","title":"36 cells / pairs / nomes / decans","state":"BANKED","why_red":"Trace actual transmission and distinguish 72/2 topology from historical dependence.","return_trigger":"New 36, paired translator, cell, nome, decan, 72/2, or 35/36 evidence.","any_terms":["36","thirty-six","35","thirty-five","decan","nome","cell","pair"],"all_terms":[],"min_hits":2},
    {"torch_id":"TORCH-MOSES-HERMES","title":"Moses–Hermes interpretation layer","state":"BANKED","why_red":"Test whether Moses/Hermes marks a mediation/interpretation layer without presuming intention or corruption.","return_trigger":"New Moses + Hermes, Artapanus, hermeneia, sacred-writing, hieroglyphic, Orpheus, or interpretation evidence.","any_terms":["moses","hermes","artapanus","hermeneia","hieroglyph","sacred letters","sacred writing","orpheus"],"all_terms":[],"min_hits":2},
    {"torch_id":"TORCH-ANGEL-FUNCTION","title":"Angel as entity vs messenger/function","state":"BANKED","why_red":"Determine when apparent entity classes are actually action/function roles such as messenger or emissary.","return_trigger":"New angel, messenger, emissary, apostle, announce, agent, demon, decan, or functional-grid evidence.","any_terms":["angel","messenger","emissary","apostle","announce","agent","demon","decan"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-SETH-VALENTINUS","title":"Seth ↔ Valentinus complementary projections","state":"BANKED","why_red":"Test whether each preserves a projection of a larger state space rather than treating one as simply wrong.","return_trigger":"New Sethian, Valentinian, Horos, Stauros, boundary, ascent/descent, or projection evidence.","any_terms":["sethian","seth","valentinian","valentinus","horos","stauros","ascent","descent"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-MUSIC","title":"Music / harmony reintegration","state":"BANKED","why_red":"Sound, phoneme, and letters must eventually reconnect to ratio, interval, pitch, inversion, and closure.","return_trigger":"New ratio, pitch, semitone, comma, interval, harmony, Kepler, Fludd, monochord, or 80:81 evidence.","any_terms":["kepler","fludd","semitone","80:81","80/81","harmony","interval","pitch","monochord","comma"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-GNOSTIC","title":"Gnostic transit operators","state":"BANKED","why_red":"Reconnect boundary, differentiation, traversal, return, and repeated-transit discoveries to the Rosetta decoder problem.","return_trigger":"New Sophia, Shem, Sethian, Valentinian, Pronoia, Horos, Pleroma, boundary, return, or traversal evidence.","any_terms":["sophia","shem","pronoia","horos","pleroma","valentinian","sethian","traversal","return"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-GOG-MAGOG","title":"Gog/Magog translation and terminal-boundary stack","state":"BURNING","why_red":"Complete Jewish/Islamic/Persian/Christian variants through the same decoder pipeline.","return_trigger":"Any Gog/Magog, years/two, hill/grave, understand/be-understood, barrier, terminal-state, or pronunciation evidence.","any_terms":["gog","magog","ya'juj","yajuj","majuj","years","two prophets","barrier","grave","elevation"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-QUAIL-SALWA","title":"Quail / salwa object-state-vector stack","state":"BURNING","why_red":"Keep event, utterance, decoder, object/state, and rise/descend vectors separate while tracing cross-language history.","return_trigger":"Any quail, salwa, consolation, manna, craving, rise, descend, or Numbers 11 evidence.","any_terms":["quail","salwa","salwā","consolation","manna","craving","rise","descend","numbers 11"],"all_terms":[],"min_hits":1},
    {"torch_id":"TORCH-ROSETTA-6X12","title":"6×12 correspondence architecture","state":"BURNING","why_red":"Discover rather than impose the six transferable classes; equal arithmetic must not collapse distinct operators.","return_trigger":"Any 6×12, 12×6, 72, six classes, twelve sectors/tribes/directions, or paired refinement evidence.","any_terms":["6x12","6×12","12x6","12×6","72","seventy-two","six classes","twelve tribes"],"all_terms":[],"min_hits":1}
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs() -> None:
    for p in (DB_DIR, INBOX_DIR, CUSTODY_DIR, ARTIFACTS_DIR, CONFIG_DIR):
        p.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_dirs()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def stable_id(prefix: str, *parts: str, length: int = 16) -> str:
    payload = "\x1f".join(parts).encode("utf-8", errors="replace")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:length].upper()}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def init_db() -> None:
    ensure_dirs()
    with connect() as con:
        con.executescript(SCHEMA)
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','0.1')")
        prior = con.execute("SELECT value FROM meta WHERE key='initialized_at'").fetchone()
        if not prior:
            con.execute("INSERT INTO meta(key,value) VALUES('initialized_at',?)", (now(),))
    if not TORCH_CONFIG.exists():
        TORCH_CONFIG.write_text(json.dumps(DEFAULT_TORCHES, ensure_ascii=False, indent=2), encoding="utf-8")
    sync_torches()


def load_torch_config() -> list[dict]:
    if not TORCH_CONFIG.exists():
        return DEFAULT_TORCHES
    try:
        data = json.loads(TORCH_CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else DEFAULT_TORCHES
    except Exception:
        return DEFAULT_TORCHES


def sync_torches() -> None:
    if not DB_PATH.exists():
        return
    ts = now()
    with connect() as con:
        for t in load_torch_config():
            con.execute(
                """INSERT INTO torches(torch_id,title,state,why_red,return_trigger,any_terms_json,all_terms_json,min_hits,source,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(torch_id) DO UPDATE SET
                    title=excluded.title,
                    state=CASE WHEN torches.state='REIGNITED' THEN torches.state ELSE excluded.state END,
                    why_red=excluded.why_red,
                    return_trigger=excluded.return_trigger,
                    any_terms_json=excluded.any_terms_json,
                    all_terms_json=excluded.all_terms_json,
                    min_hits=excluded.min_hits,
                    updated_at=excluded.updated_at""",
                (t["torch_id"],t["title"],t.get("state","BANKED"),t.get("why_red",""),t.get("return_trigger",""),json.dumps(t.get("any_terms",[]),ensure_ascii=False),json.dumps(t.get("all_terms",[]),ensure_ascii=False),int(t.get("min_hits",1)),"config",ts,ts),
            )


def extract_text(path: Path) -> tuple[Optional[str], Optional[str]]:
    ext = path.suffix.lower()
    if ext not in TEXT_EXTENSIONS:
        return None, f"No v0 text extractor for {ext or 'extensionless/binary'} input"
    try:
        if ext == ".csv":
            rows = []
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                for row in csv.reader(fh):
                    rows.append(" | ".join(row))
            return "\n".join(rows), None
        raw = path.read_text(encoding="utf-8-sig", errors="replace")
        if ext in {".html", ".htm"}:
            raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I|re.S)
            raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I|re.S)
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = html.unescape(raw)
        return raw, None
    except Exception as exc:
        return None, f"Text extraction failed: {exc}"


def line_locator(text: str, start: int) -> str:
    return f"line:{text.count(chr(10),0,start)+1}"


def bounded(value: str, limit: int = 140) -> str:
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n:;,.")
    return value if len(value) <= limit else value[:limit-1] + "…"


def insert_discrepancy(con, source_id, left, right, raw, locator, dclass="UNCLASSIFIED"):
    left,right,raw = bounded(left,80),bounded(right,80),bounded(raw,240)
    if not left or not right or left.casefold()==right.casefold(): return
    did=stable_id("DIS",source_id,left,right,locator)
    con.execute("INSERT OR IGNORE INTO discrepancies(discrepancy_id,source_id,left_value,right_value,raw_text,discrepancy_class,provenance_class,locator,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(did,source_id,left,right,raw,dclass,"MACHINE_PREDICTION",locator,now()))


def insert_transform(con, source_id, left, right, operator, raw, locator):
    left,right,raw=bounded(left,100),bounded(right,100),bounded(raw,240)
    if not left or not right or left.casefold()==right.casefold(): return
    tid=stable_id("TR",source_id,left,operator,right,locator)
    con.execute("INSERT OR IGNORE INTO transforms(transform_id,source_id,from_value,to_value,operator,raw_text,provenance_class,locator,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(tid,source_id,left,right,operator,raw,"MACHINE_PREDICTION",locator,now()))


def insert_residual(con, source_id, rtype, raw, locator):
    raw=bounded(raw,240); rid=stable_id("RES",source_id,rtype,raw,locator)
    con.execute("INSERT OR IGNORE INTO residuals(residual_id,source_id,residual_type,raw_text,locator,provenance_class,created_at) VALUES(?,?,?,?,?,?,?)",(rid,source_id,rtype,raw,locator,"MACHINE_PREDICTION",now()))


def extract_candidates(con, source_id: str, text: str) -> dict[str,int]:
    counts={"discrepancies":0,"transforms":0,"residuals":0,"assertions":0}
    transform_re=re.compile(r"(?P<a>[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9 _/×x+\-]{0,60}?)\s*(?P<op>→|↔|<->|->)\s*(?P<b>[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9 _/×x+\-]{0,60})")
    for m in transform_re.finditer(text):
        raw=text[max(0,m.start()-40):min(len(text),m.end()+40)]
        insert_transform(con,source_id,m.group("a"),m.group("b"),m.group("op"),raw,line_locator(text,m.start())); counts["transforms"]+=1
    vs_re=re.compile(r"(?P<a>[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9 _/×x+\-]{0,45}?)\s+(?:vs\.?|versus)\s+(?P<b>[A-Za-zÀ-ž0-9][A-Za-zÀ-ž0-9 _/×x+\-]{0,45})",re.I)
    for m in vs_re.finditer(text):
        raw=text[max(0,m.start()-40):min(len(text),m.end()+40)]
        insert_discrepancy(con,source_id,m.group("a"),m.group("b"),raw,line_locator(text,m.start()),"EXPLICIT_VS"); counts["discrepancies"]+=1
    pairs=[("70","72"),("35","36"),("48","49"),("5","6"),("21","22")]
    lines=text.splitlines()
    for i,line in enumerate(lines,1):
        compact=re.sub(r"[,._]","",line.casefold())
        for left,right in pairs:
            if re.search(rf"(?<!\d){left}(?!\d)",compact) and re.search(rf"(?<!\d){right}(?!\d)",compact):
                insert_discrepancy(con,source_id,left,right,line,f"line:{i}","COUNT_PAIR"); counts["discrepancies"]+=1
        if re.search(r"(?:6\s*[x×*]\s*12|12\s*[x×*]\s*6)",line,re.I):
            aid=stable_id("AST",source_id,"6x12",str(i),line)
            con.execute("INSERT OR IGNORE INTO assertions(assertion_id,source_id,kind,statement,provenance_class,locator,extraction_method,created_at) VALUES(?,?,?,?,?,?,?,?)",(aid,source_id,"FACTOR_PATTERN",bounded(line,300),"MACHINE_PREDICTION",f"line:{i}","regex:6x12",now())); counts["assertions"]+=1
        lower=line.casefold()
        for word,rtype in RESIDUAL_WORDS.items():
            if word in lower:
                insert_residual(con,source_id,rtype,line,f"line:{i}"); counts["residuals"]+=1
    markers=("hypothesis","unknown","unproven","speculative","control","bright red","must revisit","open question")
    for i,line in enumerate(lines,1):
        if any(marker in line.casefold() for marker in markers):
            aid=stable_id("AST",source_id,"EPISTEMIC_MARKER",str(i),line)
            con.execute("INSERT OR IGNORE INTO assertions(assertion_id,source_id,kind,statement,provenance_class,locator,extraction_method,created_at) VALUES(?,?,?,?,?,?,?,?)",(aid,source_id,"EPISTEMIC_MARKER",bounded(line,320),"MACHINE_PREDICTION",f"line:{i}","marker_scan",now())); counts["assertions"]+=1
    return counts


def enqueue(con, source_id, torch_id, direction, title, reason, epistemic, diagnostic):
    qid=stable_id("Q",source_id or "-",torch_id or "-",direction,title,reason)
    con.execute("INSERT OR IGNORE INTO investigation_queue(queue_id,source_id,torch_id,direction,title,reason,epistemic_support,diagnostic_value,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(qid,source_id,torch_id,direction,title,reason,epistemic,diagnostic,now()))


def match_torches(con, source_id: str, text: str) -> int:
    low=text.casefold(); hit_count=0
    for t in con.execute("SELECT * FROM torches").fetchall():
        any_terms=json.loads(t["any_terms_json"] or "[]"); all_terms=json.loads(t["all_terms_json"] or "[]")
        matched_any=[term for term in any_terms if term.casefold() in low]
        matched_all=[term for term in all_terms if term.casefold() in low]
        score=len(set(matched_any+matched_all))
        if len(matched_all)==len(all_terms) and score>=int(t["min_hits"]):
            hid=stable_id("HIT",t["torch_id"],source_id)
            con.execute("INSERT OR IGNORE INTO torch_hits(hit_id,torch_id,source_id,matched_terms_json,score,created_at) VALUES(?,?,?,?,?,?)",(hid,t["torch_id"],source_id,json.dumps(sorted(set(matched_any+matched_all)),ensure_ascii=False),score,now()))
            con.execute("UPDATE torches SET state='REIGNITED',updated_at=? WHERE torch_id=? AND state='BANKED'",(now(),t["torch_id"]))
            enqueue(con,source_id,t["torch_id"],"UP",f"Revisit: {t['title']}",f"New source matched torch terms: {', '.join(sorted(set(matched_any+matched_all)))}","MEDIUM","HIGH")
            hit_count+=1
    return hit_count


def generate_queue(con, source_id: str) -> None:
    for d in con.execute("SELECT * FROM discrepancies WHERE source_id=?",(source_id,)).fetchall():
        enqueue(con,source_id,None,"DOWN",f"Resolve discrepancy {d['left_value']} ↔ {d['right_value']}",f"Verify source form, pronunciation/reading where relevant, morphology, literal/contextual meaning, abstraction class, and downstream behavior. Candidate from {d['locator'] or 'unknown locator'}.","LOW","HIGH")
        enqueue(con,source_id,None,"SIDEWAYS",f"Search same discrepancy class elsewhere: {d['left_value']} ↔ {d['right_value']}","Look for independently attested occurrences in other traditions/languages without assuming historical dependence.","LOW","MEDIUM")
        enqueue(con,source_id,None,"ORTHOGONAL",f"Probe same address in another class: {d['left_value']} ↔ {d['right_value']}","Use correspondence/checksum systems only as search priors; do not promote them to independent evidence.","LOW","HIGH")
    for tr in con.execute("SELECT * FROM transforms WHERE source_id=?",(source_id,)).fetchall():
        enqueue(con,source_id,None,"UP",f"Global check for transform {tr['from_value']} {tr['operator']} {tr['to_value']}","Check whether this transform changes any older cosmology, lineage, language, sound/music, TOL, ritual/magic, number, or historical-transmission problem.","LOW","HIGH")


def register_source(path: Path) -> tuple[str,bool,dict[str,int]]:
    path=path.resolve(); digest=sha256_file(path); source_id=f"SRC-{digest[:16].upper()}"
    stats={"discrepancies":0,"transforms":0,"residuals":0,"assertions":0,"torch_hits":0}
    with connect() as con:
        existing=con.execute("SELECT source_id FROM sources WHERE sha256=?",(digest,)).fetchone()
        if existing: return existing["source_id"],False,stats
        dest_dir=CUSTODY_DIR/source_id; dest_dir.mkdir(parents=True,exist_ok=True); dest=dest_dir/path.name
        if not dest.exists(): shutil.copy2(path,dest)
        text,error=extract_text(path)
        con.execute("INSERT INTO sources(source_id,sha256,original_name,original_path,custody_path,extension,byte_size,text_extracted,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(source_id,digest,path.name,str(path),str(dest.relative_to(ROOT)),path.suffix.lower(),path.stat().st_size,1 if text is not None else 0,now()))
        eid=stable_id("EVT",source_id,"INGEST",now())
        con.execute("INSERT INTO ingest_events(event_id,source_id,action,detail,created_at) VALUES(?,?,?,?,?)",(eid,source_id,"INGEST","Source registered in custody",now()))
        if text is None:
            insert_residual(con,source_id,"UNEXTRACTED_SOURCE",error or "No text extracted","source"); stats["residuals"]+=1
        else:
            stats.update(extract_candidates(con,source_id,text)); stats["torch_hits"]=match_torches(con,source_id,text); generate_queue(con,source_id)
    return source_id,True,stats


def inbox_files() -> Iterable[Path]:
    ensure_dirs()
    for p in sorted(INBOX_DIR.rglob("*")):
        if p.is_file() and not p.name.startswith("."): yield p


def ingest(paths: list[str]) -> None:
    init_db(); candidates=[Path(p) for p in paths] if paths else list(inbox_files())
    if not candidates:
        print(f"ARIADNE: inbox is empty: {INBOX_DIR}"); print("Drop material there and run: python ariadne.py ingest"); return
    new_count=0
    for p in candidates:
        if not p.exists() or not p.is_file(): print(f"SKIP: {p} (not a file)"); continue
        source_id,is_new,stats=register_source(p)
        if is_new:
            new_count+=1; print(f"INGESTED {p.name} -> {source_id} | discrepancies={stats['discrepancies']} transforms={stats['transforms']} residuals={stats['residuals']} torch_hits={stats['torch_hits']}")
        else: print(f"KNOWN    {p.name} -> {source_id}")
    print(f"ARIADNE: {new_count} new source(s) registered.")


def esc(v) -> str: return html.escape("" if v is None else str(v))


def rows_table(headers, rows, empty="None yet.") -> str:
    data=list(rows)
    if not data: return f"<p class='muted'>{esc(empty)}</p>"
    th="".join(f"<th>{esc(h)}</th>" for h in headers)
    trs=["<tr>"+"".join(f"<td>{esc(v)}</td>" for v in row)+"</tr>" for row in data]
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"


def report(open_browser: bool=False) -> Path:
    init_db()
    with connect() as con:
        counts={t:con.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"] for t in ("sources","assertions","discrepancies","transforms","residuals","torches","torch_hits","investigation_queue")}
        sources=con.execute("SELECT source_id,original_name,text_extracted,created_at FROM sources ORDER BY created_at DESC LIMIT 50").fetchall()
        torches=con.execute("SELECT torch_id,title,state,why_red,return_trigger FROM torches ORDER BY CASE state WHEN 'REIGNITED' THEN 0 WHEN 'BURNING' THEN 1 ELSE 2 END,title").fetchall()
        hits=con.execute("SELECT h.created_at,t.title,s.original_name,h.score,h.matched_terms_json FROM torch_hits h JOIN torches t USING(torch_id) JOIN sources s USING(source_id) ORDER BY h.created_at DESC LIMIT 100").fetchall()
        discrepancies=con.execute("SELECT d.discrepancy_id,s.original_name,d.left_value,d.right_value,d.discrepancy_class,d.locator FROM discrepancies d JOIN sources s USING(source_id) ORDER BY d.created_at DESC LIMIT 100").fetchall()
        transforms=con.execute("SELECT tr.transform_id,s.original_name,tr.from_value,tr.operator,tr.to_value,tr.locator FROM transforms tr JOIN sources s USING(source_id) ORDER BY tr.created_at DESC LIMIT 100").fetchall()
        residuals=con.execute("SELECT r.residual_id,s.original_name,r.residual_type,r.raw_text,r.locator FROM residuals r JOIN sources s USING(source_id) ORDER BY r.created_at DESC LIMIT 100").fetchall()
        queue=con.execute("SELECT q.queue_id,q.direction,q.title,q.epistemic_support,q.diagnostic_value,COALESCE(s.original_name,''),COALESCE(t.title,'') FROM investigation_queue q LEFT JOIN sources s USING(source_id) LEFT JOIN torches t USING(torch_id) WHERE q.status='OPEN' ORDER BY CASE q.diagnostic_value WHEN 'EXTREME' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,q.created_at DESC LIMIT 200").fetchall()
    cards="".join(f"<div class='card'><div class='num'>{counts[k]}</div><div class='label'>{esc(label)}</div></div>" for k,label in [("sources","Sources"),("discrepancies","Discrepancies"),("transforms","Transforms"),("residuals","Residuals"),("torch_hits","Torch hits"),("investigation_queue","Open searches")])
    page=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ARIADNE — What Changed?</title><style>
:root{{color-scheme:dark;--bg:#111318;--panel:#1a1e26;--line:#303744;--text:#edf1f7;--muted:#9ba7b7;--accent:#d8ba72}}*{{box-sizing:border-box}}body{{margin:0;font:15px/1.45 system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--text)}}main{{max-width:1500px;margin:auto;padding:28px}}h1{{margin:.1em 0;font-size:34px}}h2{{margin-top:36px;border-bottom:1px solid var(--line);padding-bottom:8px}}.subtitle,.muted{{color:var(--muted)}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}}.num{{font-size:30px;font-weight:700;color:var(--accent)}}.label{{color:var(--muted)}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:800px;background:var(--panel)}}th,td{{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--line)}}th{{position:sticky;top:0;background:#222833}}.notice{{border-left:4px solid var(--accent);padding:12px 16px;background:var(--panel);margin:18px 0}}</style></head><body><main>
<h1>ARIADNE</h1><div class='subtitle'>What changed? · generated {esc(now())}</div><div class='notice'><strong>Epistemic firewall:</strong> automated detections below are candidates. They do not become historical truth by appearing in this report.</div><div class='cards'>{cards}</div>
<h2>Where to look next</h2>{rows_table(['ID','Direction','Investigation','Epistemic support','Diagnostic value','Source','Torch'],queue,'No open investigation candidates yet.')}
<h2>Torches</h2>{rows_table(['ID','Title','State','Why red','Return trigger'],([t['torch_id'],t['title'],t['state'],t['why_red'],t['return_trigger']] for t in torches))}
<h2>Reignitions / torch hits</h2>{rows_table(['When','Torch','Source','Score','Matched terms'],([h['created_at'],h['title'],h['original_name'],h['score'],h['matched_terms_json']] for h in hits),'No torch hits yet.')}
<h2>Discrepancies</h2>{rows_table(['ID','Source','A','B','Class','Locator'],discrepancies,'No discrepancy candidates yet.')}
<h2>Transforms</h2>{rows_table(['ID','Source','From','Operator','To','Locator'],transforms,'No transform candidates yet.')}
<h2>Residuals / outliers</h2>{rows_table(['ID','Source','Type','Raw evidence','Locator'],residuals,'No residuals recorded yet.')}
<h2>Source custody</h2>{rows_table(['Source ID','Original name','Text extracted','Ingested'],([s['source_id'],s['original_name'],'yes' if s['text_extracted'] else 'no',s['created_at']] for s in sources),'No sources ingested yet.')}
</main></body></html>"""
    ensure_dirs(); REPORT_PATH.write_text(page,encoding="utf-8"); print(f"REPORT: {REPORT_PATH}")
    if open_browser: webbrowser.open(REPORT_PATH.as_uri())
    return REPORT_PATH


def status() -> None:
    init_db()
    with connect() as con:
        src=con.execute("SELECT COUNT(*) n FROM sources").fetchone()["n"]; q=con.execute("SELECT COUNT(*) n FROM investigation_queue WHERE status='OPEN'").fetchone()["n"]; reignited=con.execute("SELECT COUNT(*) n FROM torches WHERE state='REIGNITED'").fetchone()["n"]
        print(f"ARIADNE v0 | sources={src} | open_searches={q} | reignited_torches={reignited}")
        for row in con.execute("SELECT title,state FROM torches WHERE state IN ('REIGNITED','BURNING') ORDER BY state DESC,title"): print(f"  {row['state']:<9} {row['title']}")


def main(argv: Optional[list[str]]=None) -> int:
    parser=argparse.ArgumentParser(description="ARIADNE v0 — auditable evidence-navigation engine"); sub=parser.add_subparsers(dest="command")
    sub.add_parser("init",help="Initialize folders, SQLite ledger, and default torch registry")
    p_ingest=sub.add_parser("ingest",help="Ingest files; with no paths, ingest the inbox recursively"); p_ingest.add_argument("paths",nargs="*",help="Optional files to ingest directly")
    p_report=sub.add_parser("report",help="Generate artifacts/latest_report.html"); p_report.add_argument("--open",action="store_true",help="Open report in the default browser")
    sub.add_parser("status",help="Show compact project status")
    p_run=sub.add_parser("run",help="Ingest inbox then generate/open the report"); p_run.add_argument("--no-open",action="store_true",help="Do not open browser")
    args=parser.parse_args(argv); cmd=args.command or "run"
    if cmd=="init": init_db(); print(f"ARIADNE initialized at {ROOT}")
    elif cmd=="ingest": ingest(args.paths)
    elif cmd=="report": report(args.open)
    elif cmd=="status": status()
    elif cmd=="run": ingest([]); report(not args.no_open)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
