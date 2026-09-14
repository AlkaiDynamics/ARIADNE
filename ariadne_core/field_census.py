"""P0 prior-art / field-census gate.

ARIADNE researches the research landscape before original synthesis. Bibliographic
index records are G0 discovery guidance: they can establish that a record exists
and teach search vocabulary, but they do not establish the historical/scientific
claims discussed by the indexed work.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

from .store import encoded, event, identity

PROVIDERS = ("openalex", "crossref", "openlibrary")
STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could",
    "did","do","does","for","from","had","has","have","how","if","in","into","is",
    "it","its","may","of","on","or","our","that","the","their","then","there",
    "these","this","those","to","under","was","were","what","when","where","which",
    "while","who","why","with","within","would","yet","work","works","research",
    "field","idea","model","models","theory","theories","study","studies"
}
REVIEW_TERMS = ("review", "survey", "bibliography", "historiography", "handbook", "overview")

SCHEMA = """
CREATE TABLE IF NOT EXISTS research_questions (
 question_id TEXT PRIMARY KEY, question TEXT NOT NULL, scope TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('CENSUS','READY','SATURATED','PAUSED')),
 seed_terms TEXT NOT NULL, source TEXT NOT NULL, created_at REAL NOT NULL,
 updated_at REAL NOT NULL, gate_reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS field_queries (
 field_query_id TEXT PRIMARY KEY,
 question_id TEXT NOT NULL REFERENCES research_questions(question_id),
 provider TEXT NOT NULL, round_no INTEGER NOT NULL, query_text TEXT NOT NULL,
 job_id TEXT NOT NULL REFERENCES acquisition_jobs(job_id),
 status TEXT NOT NULL DEFAULT 'QUEUED', created_at REAL NOT NULL,
 UNIQUE(question_id,provider,round_no,query_text));
CREATE TABLE IF NOT EXISTS field_candidates (
 candidate_id TEXT PRIMARY KEY,
 field_query_id TEXT NOT NULL REFERENCES field_queries(field_query_id),
 question_id TEXT NOT NULL REFERENCES research_questions(question_id),
 provider TEXT NOT NULL, external_id TEXT NOT NULL, canonical_key TEXT NOT NULL,
 title TEXT NOT NULL, authors TEXT NOT NULL, year INTEGER, work_type TEXT NOT NULL,
 doi TEXT, url TEXT, subjects TEXT NOT NULL, cited_by_count INTEGER NOT NULL,
 selected INTEGER NOT NULL DEFAULT 0,
 evidence_scope TEXT NOT NULL DEFAULT 'PRIOR_ART_DISCOVERY_METADATA_ONLY',
 historical_authority TEXT NOT NULL DEFAULT 'NONE_FOR_UNDERLYING_HISTORICAL_CLAIMS',
 data TEXT NOT NULL,
 UNIQUE(field_query_id,provider,external_id));
CREATE INDEX IF NOT EXISTS field_candidate_question ON field_candidates(question_id,canonical_key);
"""


def install(con):
    con.executescript(SCHEMA)


def settings(config=None):
    c = config or {}
    providers = c.get("field_census_providers", list(PROVIDERS))
    if not isinstance(providers, list) or not providers or any(x not in PROVIDERS for x in providers):
        providers = list(PROVIDERS)
    values = {
        "required": c.get("field_census_required", True),
        "providers": providers,
        "min_providers": c.get("field_census_min_providers", 2),
        "rounds": c.get("field_census_rounds", 2),
        "surface_k": c.get("field_census_surface_k", 12),
        "expansion_terms": c.get("field_census_expansion_terms", 2),
        "saturation_novelty": c.get("field_census_saturation_novelty", .25),
    }
    if type(values["required"]) is not bool:
        raise ValueError("field_census_required must be boolean")
    for key in ("min_providers","rounds","surface_k","expansion_terms"):
        if type(values[key]) is not int or values[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if not isinstance(values["saturation_novelty"], (int,float)) or not math.isfinite(values["saturation_novelty"]) or not 0 <= values["saturation_novelty"] <= 1:
        raise ValueError("field_census_saturation_novelty must be in [0,1]")
    return values


def _tokens(text):
    return [x.casefold() for x in re.findall(r"[^\W_][\w'/-]{1,}", text or "", flags=re.UNICODE)]


def _terms(text):
    return [x for x in _tokens(text) if len(x) >= 3 and x not in STOPWORDS]


def _doi(value):
    if not value:
        return None
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(value).strip(), flags=re.I)
    return value or None


def _year(value):
    try:
        parts = value.get("date-parts", [])
        return int(parts[0][0]) if parts and parts[0] else None
    except (AttributeError, TypeError, ValueError, IndexError):
        return None


def provider_url(provider, query):
    query = " ".join(query.split())[:240]
    if provider == "openalex":
        return "https://api.openalex.org/works?" + urlencode({"search":query,"per-page":25})
    if provider == "crossref":
        return "https://api.crossref.org/works?" + urlencode({"query.bibliographic":query,"rows":25})
    if provider == "openlibrary":
        return "https://openlibrary.org/search.json?" + urlencode({
            "q":query,"limit":25,"fields":"key,title,author_name,first_publish_year,subject"})
    raise ValueError(f"unsupported provider: {provider}")


def register_question(con, question, scope="", seed_terms=None, source="USER"):
    question = " ".join(str(question).split())
    scope = " ".join(str(scope or "").split())
    seeds = [" ".join(str(x).split()) for x in (seed_terms or []) if str(x).strip()]
    if len(question) < 5:
        raise ValueError("research question must be at least five characters")
    qid = identity("RQ", question, scope)
    cur = con.execute("""INSERT OR IGNORE INTO research_questions
        (question_id,question,scope,status,seed_terms,source,created_at,updated_at,gate_reason)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (qid,question,scope,"CENSUS",encoded(seeds),source,time.time(),time.time(),
         "P0 field census has not completed"))
    if cur.rowcount:
        event(con,"P0_QUESTION",qid,{"question":question,"scope":scope,"seed_terms":seeds})
    return qid


def sync_question_config(con, root):
    path = Path(root)/"config/research_questions.json"
    if not path.exists():
        return 0
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        event(con,"P0_CONFIG_ERROR",str(path),{"error":str(exc)})
        return 0
    if not isinstance(rows,list):
        event(con,"P0_CONFIG_ERROR",str(path),{"error":"expected a list"})
        return 0
    before = con.execute("SELECT COUNT(*) FROM research_questions").fetchone()[0]
    for row in rows:
        if isinstance(row,dict) and row.get("enabled",True):
            register_question(con,row.get("question",""),row.get("scope",""),row.get("seed_terms",[]),"CONFIG")
    return con.execute("SELECT COUNT(*) FROM research_questions").fetchone()[0]-before


def _queue(con, qid, provider, round_no, query):
    from .acquisition import queue_manifest
    url = provider_url(provider,query)
    queue_manifest(con,url,origin=qid,depth=0,relation="FIELD_CENSUS_SEARCH")
    job = identity("ACQ",url)
    fid = identity("FQ",qid,provider,round_no,query)
    con.execute("""INSERT OR IGNORE INTO field_queries
        (field_query_id,question_id,provider,round_no,query_text,job_id,status,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",(fid,qid,provider,round_no,query,job,"QUEUED",time.time()))
    return fid


def ensure_initial_queries(con, qid, config=None):
    s = settings(config)
    if con.execute("SELECT 1 FROM field_queries WHERE question_id=? LIMIT 1",(qid,)).fetchone():
        return 0
    row = con.execute("SELECT * FROM research_questions WHERE question_id=?",(qid,)).fetchone()
    if not row or row["status"] == "PAUSED":
        return 0
    seeds = json.loads(row["seed_terms"])
    core = " ".join(_terms(row["question"])[:14])
    query = " ".join([core,*seeds[:3]]).strip() or row["question"]
    count = 0
    for provider in s["providers"]:
        _queue(con,qid,provider,0,query); count += 1
    event(con,"P0_FIELD_SEARCH_QUEUED",qid,{"round":0,"query":query,"providers":s["providers"]})
    return count


def ensure_all(con, config=None):
    return sum(ensure_initial_queries(con,r[0],config) for r in con.execute(
        "SELECT question_id FROM research_questions WHERE status='CENSUS' ORDER BY question_id").fetchall())


def _canonical(title, year, doi):
    if doi:
        return "doi:"+doi.casefold()
    return identity("WORK"," ".join(_tokens(title)),year)


def _candidate(field_query, external_id, title, authors, year, work_type, doi, url, subjects, cited, raw):
    title = " ".join(str(title or "").split())
    if not title:
        return None
    doi = _doi(doi)
    return (
        identity("FC",field_query["field_query_id"],field_query["provider"],str(external_id)),
        field_query["field_query_id"],field_query["question_id"],field_query["provider"],
        str(external_id),_canonical(title,year,doi),title,encoded([str(x) for x in authors if x]),
        year if isinstance(year,int) else None,str(work_type or ""),doi,str(url or ""),
        encoded([str(x) for x in subjects if x][:40]),int(cited or 0),0,
        "PRIOR_ART_DISCOVERY_METADATA_ONLY","NONE_FOR_UNDERLYING_HISTORICAL_CLAIMS",encoded(raw))


def _parse(field_query, body):
    obj = json.loads(body.decode("utf-8",errors="replace"))
    out = []
    if field_query["provider"] == "openalex":
        for x in obj.get("results",[]):
            authors=[a.get("author",{}).get("display_name","") for a in x.get("authorships",[]) if isinstance(a,dict)]
            subjects=[]
            if isinstance(x.get("primary_topic"),dict):subjects.append(x["primary_topic"].get("display_name",""))
            subjects += [t.get("display_name","") for t in x.get("topics",[])[:10] if isinstance(t,dict)]
            out.append(_candidate(field_query,x.get("id"),x.get("display_name") or x.get("title"),authors,
                x.get("publication_year"),x.get("type"),x.get("doi"),x.get("doi") or x.get("id"),subjects,x.get("cited_by_count",0),x))
    elif field_query["provider"] == "crossref":
        for x in obj.get("message",{}).get("items",[]):
            authors=[" ".join(y for y in (a.get("given",""),a.get("family","")) if y) for a in x.get("author",[]) if isinstance(a,dict)]
            title=(x.get("title") or [""])[0]
            year=_year(x.get("published-print") or x.get("published-online") or x.get("issued") or {})
            out.append(_candidate(field_query,x.get("DOI") or identity("EXT",title,year),title,authors,year,
                x.get("type"),x.get("DOI"),x.get("URL"),x.get("subject",[]),x.get("is-referenced-by-count",0),x))
    elif field_query["provider"] == "openlibrary":
        for x in obj.get("docs",[]):
            key=x.get("key") or identity("EXT",x.get("title"),x.get("first_publish_year"))
            url="https://openlibrary.org"+key if str(key).startswith("/") else ""
            out.append(_candidate(field_query,key,x.get("title"),x.get("author_name",[]),x.get("first_publish_year"),
                "book/catalog-record",None,url,x.get("subject",[])[:20],0,x))
    return [x for x in out if x]


def _vocabulary(con, qid):
    question = con.execute("SELECT question FROM research_questions WHERE question_id=?",(qid,)).fetchone()[0]
    excluded=set(_terms(question)); counts=Counter()
    for row in con.execute("SELECT title,subjects FROM field_candidates WHERE question_id=?",(qid,)):
        counts.update(x for x in _terms(row["title"]) if x not in excluded)
        for subject in json.loads(row["subjects"]):
            counts.update(x for x in _terms(subject) if x not in excluded)
    return counts


def _round_done(con, qid, round_no, providers):
    rows=con.execute("SELECT provider,status FROM field_queries WHERE question_id=? AND round_no=?",(qid,round_no)).fetchall()
    present={r["provider"] for r in rows}; terminal={"PARSED","FAILED","BLOCKED"}
    return set(providers)<=present and all(r["status"] in terminal for r in rows)


def _refresh_status(con, qid, config):
    s=settings(config); row=con.execute("SELECT * FROM research_questions WHERE question_id=?",(qid,)).fetchone()
    if not row or row["status"]=="PAUSED":return
    parsed={r[0] for r in con.execute("SELECT DISTINCT provider FROM field_queries WHERE question_id=? AND status='PARSED'",(qid,))}
    max_round=s["rounds"]-1
    completed=[n for n in range(s["rounds"]) if _round_done(con,qid,n,s["providers"])]
    unique=con.execute("SELECT COUNT(DISTINCT canonical_key) FROM field_candidates WHERE question_id=?",(qid,)).fetchone()[0]
    if 0 in completed and s["rounds"]>1 and not con.execute("SELECT 1 FROM field_queries WHERE question_id=? AND round_no=1 LIMIT 1",(qid,)).fetchone():
        vocab=_vocabulary(con,qid); seeds=json.loads(row["seed_terms"])
        expansion=[t for t,_ in vocab.most_common(s["expansion_terms"])] or [x for x in seeds if x][:s["expansion_terms"]]
        if not expansion: expansion=_terms(row["question"])[:s["expansion_terms"]]
        base=" ".join(_terms(row["question"])[:10])
        for term in expansion:
            query=" ".join([base,term]).strip()
            for provider in s["providers"]:_queue(con,qid,provider,1,query)
        event(con,"P0_FIELD_EXPANSION",qid,{"terms":expansion,"providers":s["providers"]})
        con.execute("UPDATE research_questions SET updated_at=?,gate_reason=? WHERE question_id=?",
                    (time.time(),"Vocabulary expansion round queued",qid));return
    if len(parsed)>=s["min_providers"] and max_round in completed:
        r0={r[0] for r in con.execute("""SELECT DISTINCT c.canonical_key FROM field_candidates c
             JOIN field_queries q USING(field_query_id) WHERE c.question_id=? AND q.round_no=0""",(qid,))}
        rn={r[0] for r in con.execute("""SELECT DISTINCT c.canonical_key FROM field_candidates c
             JOIN field_queries q USING(field_query_id) WHERE c.question_id=? AND q.round_no=?""",(qid,max_round))}
        novelty=len(rn-r0)/len(rn) if rn else 0.0
        status="SATURATED" if novelty<=s["saturation_novelty"] else "READY"
        reason=("No applicable prior art found in the bounded census" if unique==0 else
                f"Field map established across {len(parsed)} providers; final-round novelty={novelty:.3f}; unique works={unique}")
        con.execute("UPDATE research_questions SET status=?,updated_at=?,gate_reason=? WHERE question_id=?",
                    (status,time.time(),reason,qid))
        event(con,"P0_GATE_OPEN",qid,{"status":status,"reason":reason,"providers":sorted(parsed),"unique_works":unique,"novelty":novelty})
    else:
        con.execute("UPDATE research_questions SET updated_at=?,gate_reason=? WHERE question_id=?",
                    (time.time(),f"Field census in progress; providers parsed={len(parsed)}/{s['min_providers']}",qid))


def process(con, root, config=None):
    """Parse acquired bibliographic index responses and advance the P0 gate."""
    processed=0
    rows=con.execute("""SELECT q.*,j.status job_status,j.source_id,j.detail
        FROM field_queries q JOIN acquisition_jobs j USING(job_id)
        WHERE q.status='QUEUED' ORDER BY q.round_no,q.field_query_id""").fetchall()
    terminal={"AUTH_REQUIRED","PAYWALLED","ROBOTS_BLOCKED","BANKED_DEPTH","UNSUPPORTED_FORMAT"}
    for row in rows:
        if row["source_id"]:
            source=con.execute("SELECT custody_path FROM sources WHERE source_id=?",(row["source_id"],)).fetchone()
            try:
                body=(Path(root)/source[0]).read_bytes(); candidates=_parse(row,body)
                con.executemany("""INSERT OR IGNORE INTO field_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",candidates)
                con.execute("UPDATE field_queries SET status='PARSED' WHERE field_query_id=?",(row["field_query_id"],))
                event(con,"P0_FIELD_RESULT",row["field_query_id"],{"provider":row["provider"],"records":len(candidates),"scope":"G0_DISCOVERY_METADATA"})
            except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
                con.execute("UPDATE field_queries SET status='FAILED' WHERE field_query_id=?",(row["field_query_id"],))
                event(con,"P0_FIELD_RESULT_FAILED",row["field_query_id"],{"provider":row["provider"],"error":str(exc)})
            processed+=1
        elif row["job_status"] in terminal or (row["job_status"]=="FETCH_FAILED" and json.loads(row["detail"] or "{}").get("error")):
            con.execute("UPDATE field_queries SET status='BLOCKED' WHERE field_query_id=?",(row["field_query_id"],));processed+=1
    for q in con.execute("SELECT question_id FROM research_questions WHERE status='CENSUS' ORDER BY question_id").fetchall():
        _refresh_status(con,q[0],config)
    return processed


def gate_status(con, config=None):
    s=settings(config)
    if not s["required"]:
        return {"required":False,"blocked":False,"questions":[]}
    rows=[dict(r) for r in con.execute("SELECT question_id,question,status,gate_reason FROM research_questions ORDER BY created_at,question_id")]
    blocked=[r for r in rows if r["status"]=="CENSUS"]
    return {"required":True,"blocked":bool(blocked),"questions":rows,"blocked_questions":blocked}


def field_map(con, qid, surface_k=12):
    q=con.execute("SELECT * FROM research_questions WHERE question_id=?",(qid,)).fetchone()
    if not q:return None
    grouped={}
    for row in con.execute("SELECT * FROM field_candidates WHERE question_id=?",(qid,)):
        item=grouped.setdefault(row["canonical_key"],{"title":row["title"],"year":row["year"],"doi":row["doi"],"url":row["url"],"authors":json.loads(row["authors"]),"providers":set(),"citations":0,"types":set()})
        item["providers"].add(row["provider"]);item["citations"]=max(item["citations"],row["cited_by_count"]);item["types"].add(row["work_type"])
        if not item["doi"] and row["doi"]:item["doi"]=row["doi"]
        if not item["url"] and row["url"]:item["url"]=row["url"]
    works=list(grouped.values())
    for item in works:
        review=any(term in item["title"].casefold() for term in REVIEW_TERMS)
        item["score"]=100*len(item["providers"])+(25 if review else 0)+math.log1p(item["citations"])
        item["providers"]=sorted(item["providers"]);item["types"]=sorted(x for x in item["types"] if x)
    works.sort(key=lambda x:(-x["score"],-(x["year"] or 0),x["title"]))
    vocab=_vocabulary(con,qid).most_common(20)
    return {"question":dict(q),"unique_works":len(works),"vocabulary":vocab,"top_works":works[:surface_k]}


def queue_prior_art_leads(con, qid, limit=12):
    """Acquire surfaced scholarship after P0 opens; papers remain E0 until verified by scope."""
    from .acquisition import queue_manifest
    fmap=field_map(con,qid,limit)
    if not fmap or fmap["question"]["status"] not in ("READY","SATURATED"):
        return 0
    count=0
    for work in fmap["top_works"]:
        pointer=("https://doi.org/"+work["doi"]) if work["doi"] else work["url"]
        if pointer:
            count+=queue_manifest(con,pointer,origin=qid,depth=0,relation="PRIOR_ART_LEAD")
    event(con,"P0_PRIOR_ART_LEADS",qid,{"queued":count,"surface_k":limit})
    return count
