"""Persistent model-free URL/DOI acquisition and citation-pointer expansion."""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from .store import encoded, event, identity

USER_AGENT='ARIADNE/1.0 (local research source custody)'
MAX_BYTES=25*1024*1024
_LAST_REQUEST={}


def infer_lane(path,text):
    name=path.name.casefold()
    if any(x in name for x in ('chat','conversation','checkpoint')):
        return 'G0','Recognized conversation filename; guidance only'
    try:
        obj=json.loads(text)
        if isinstance(obj,dict) and (obj.get('lane')=='G0' or obj.get('source',{}).get('lane')=='G0' or 'messages' in obj or 'mapping' in obj):
            return 'G0','Recognized chat/checkpoint envelope'
        if isinstance(obj,list) and any(isinstance(x,dict) and ('mapping' in x or 'messages' in x) for x in obj):
            return 'G0','Recognized conversation export list'
    except (ValueError,AttributeError):
        pass
    if re.search(r'(?im)^(?:user|assistant|human|chatgpt)\s*:',text):
        return 'G0','Recognized transcript role markers'
    return 'E0','Unverified candidate source; no automatic E1 promotion'


def pointers(text):
    """Parse a messy manifest. Unknown identifiers are retained separately by caller."""
    found=re.findall(r'https?://[^\s<>"\]]+',text)
    found += ['https://doi.org/'+m for m in re.findall(r'(?i)(?:doi\s*:\s*|(?<![\w/]))(10\.\d{4,9}/[^\s<>"\]]+)',text)]
    found += ['https://arxiv.org/abs/'+m for m in re.findall(r'(?i)arxiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)',text)]
    result=[]
    for value in found:
        value=value.rstrip('.,;)]}')
        parts=urlsplit(value)
        if parts.scheme in ('http','https') and parts.hostname:
            # Preserve case-sensitive paths/queries; strip navigation fragments only.
            value=urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path or '/',parts.query,''))
            result.append(value)
    return sorted(set(result))


def queue_manifest(con,text,origin='USER_RESEARCH_MANIFEST',depth=0,relation='POINTER'):
    urls=pointers(text)
    for url in urls:
        jid=identity('ACQ',url)
        con.execute('INSERT OR IGNORE INTO acquisition_jobs(job_id,url,discovered_from,depth,status) VALUES(?,?,?,?,?)',
                    (jid,url,origin,depth,'QUEUED' if depth<=2 else 'BANKED_DEPTH'))
        con.execute('INSERT OR IGNORE INTO acquisition_links VALUES(?,?,?)',(origin,jid,relation))
    event(con,'ACQUISITION_MANIFEST',origin,{'urls':urls,'raw_manifest':text,'unsupported_identifiers':'Retained in raw manifest; ISBN and bare work titles require an adapter'})
    return len(urls)


def public_target(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTP(S) URLs without credentials are supported')
    if p.port not in (None,80,443):
        raise ValueError('Unsupported URL port')
    addresses=sorted({x[4][0] for x in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError('Private, loopback and non-public destinations are blocked')
    return p,addresses[0]


def request_once(url,limit=MAX_BYTES):
    """Pin the validated IP while preserving HTTPS hostname verification and SNI."""
    p,address=public_target(url)
    wait=1-(time.monotonic()-_LAST_REQUEST.get(p.hostname,0))
    if wait>0:time.sleep(wait)
    _LAST_REQUEST[p.hostname]=time.monotonic()
    port=p.port or (443 if p.scheme=='https' else 80)
    conn=http.client.HTTPConnection(p.hostname,port,timeout=15)
    sock=socket.create_connection((address,port),timeout=15)
    if p.scheme=='https':
        try:sock=ssl.create_default_context().wrap_socket(sock,server_hostname=p.hostname)
        except BaseException:
            sock.close();raise
    conn.sock=sock
    try:
        path=urlunsplit(('','',p.path or '/',p.query,''))
        conn.request('GET',path,headers={'User-Agent':USER_AGENT,'Accept-Encoding':'identity'})
        response=conn.getresponse()
        chunks=[];size=0;deadline=time.monotonic()+30
        while size<=limit:
            if time.monotonic()>deadline:raise ValueError('Response download deadline exceeded')
            chunk=response.read1(min(65536,limit+1-size))
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
        data=b''.join(chunks)
        if len(data)>limit:
            raise ValueError('Source exceeds configured 25 MiB acquisition bound')
        return response.status,dict(response.getheaders()),data
    finally:
        conn.close()


def fetch(url,robots=True):
    visited=[]
    for _ in range(8):
        if url in visited:raise ValueError('Redirect cycle')
        visited.append(url)
        if robots:
            p,_=public_target(url)
            robots_url=urlunsplit((p.scheme,p.netloc,'/robots.txt','',''))
            code,headers,body=request_once(robots_url,limit=512*1024)
            if code==200:
                policy=RobotFileParser();policy.parse(body.decode('utf-8',errors='replace').splitlines())
                if not policy.can_fetch(USER_AGENT,url):return 'ROBOTS_BLOCKED',None,{'url':url,'redirects':visited}
                delay=policy.crawl_delay(USER_AGENT)
                if delay and delay>1:
                    return 'ROBOTS_BLOCKED',None,{'url':url,'reason':'crawl delay exceeds current adapter rate; retained for later adapter'}
            elif code in (401,403):
                return 'ROBOTS_BLOCKED',None,{'url':url,'robots_status':code}
            elif code!=404:
                return 'FETCH_FAILED',None,{'url':url,'reason':'robots policy unavailable','robots_status':code}
        code,headers,body=request_once(url)
        headers={k.lower():v for k,v in headers.items()}
        if code in (301,302,303,307,308):
            if 'location' not in headers:raise ValueError('Redirect has no location')
            url=urljoin(url,headers['location']);continue
        meta=dict(url=url,http_status=code,headers=headers,redirects=visited,retrieved_at=time.time())
        if code in (401,403):return 'AUTH_REQUIRED',None,meta
        if code==402:return 'PAYWALLED',None,meta
        if code==429 or code>=500:return 'FETCH_FAILED',None,meta
        if code!=200:return 'FETCH_FAILED',None,meta
        return 'FETCHED',body,meta
    raise ValueError('Redirect budget exceeded')


def acquire(con,root,budget=4,fetcher=fetch):
    """Finite acquisition batch. Backoff and all failures are persisted, never absence."""
    import ariadne
    if type(budget) is not int or budget<0:raise ValueError('acquisition budget must be nonnegative')
    done=0
    rows=con.execute("SELECT * FROM acquisition_jobs WHERE status IN ('QUEUED','FETCH_FAILED') AND attempts<3 AND next_attempt<=? ORDER BY depth,attempts,job_id LIMIT ?",(time.time(),budget)).fetchall()
    for job in rows:
        try:
            p=urlsplit(job['url'])
            parts=p.path.strip('/').split('/')
            if p.hostname=='github.com' and len(parts)==2 and all(re.fullmatch(r'[A-Za-z0-9_.-]+',x) for x in parts):
                repo='/'.join(parts).removesuffix('.git')
                queue_manifest(con,f'https://api.github.com/repos/{repo}\nhttps://raw.githubusercontent.com/{repo}/HEAD/README.md\nhttps://api.github.com/repos/{repo}/git/trees/HEAD',job['job_id'],job['depth']+1,'REPO_ADAPTER')
            # Do not hold SQLite's writer lock across network I/O.
            con.commit()
            status,body,detail=fetcher(job['url'])
            con.execute('UPDATE acquisition_jobs SET status=?,attempts=attempts+1,next_attempt=?,detail=? WHERE job_id=?',
                        (status,time.time()+30*2**job['attempts'],encoded(detail),job['job_id']))
            if body is not None:
                headers=detail.get('headers',{})
                mime=headers.get('content-type','').split(';')[0]
                ext={ 'application/pdf':'.pdf','text/html':'.html','text/plain':'.txt','application/json':'.json','text/csv':'.csv'}.get(mime,Path(urlsplit(detail.get('url',job['url'])).path).suffix or '.bin')
                if not re.fullmatch(r'\.[A-Za-z0-9]{1,10}',ext):ext='.bin'
                directory=Path(root)/'inbox/acquired';directory.mkdir(parents=True,exist_ok=True)
                digest=hashlib.sha256(body).hexdigest();path=directory/(digest+ext)
                if not path.exists():
                    temporary=path.with_suffix('.part');temporary.write_bytes(body);temporary.replace(path)
                sid,is_new,_=ariadne.register_source(path,connection=con,pointer_depth=job['depth']+1)
                con.execute("UPDATE acquisition_jobs SET status='CUSTODIED',source_id=? WHERE job_id=?",(sid,job['job_id']))
                detail.update(sha256=digest,duplicate=not is_new)
                if mime in ('text/html','text/plain','application/json'):
                    raw=body.decode('utf-8',errors='replace')
                    # Explicit DOI/citation/link pointers only; labels do not claim actual citation semantics.
                    leads=pointers(raw)
                    queue_manifest(con,'\n'.join(leads),job['job_id'],job['depth']+1,'DISCOVERED_POINTER')
                event(con,'ACQUISITION_CUSTODY',job['job_id'],dict(detail,source_id=sid))
            event(con,'ACQUISITION_RESULT',job['job_id'],dict(detail,status=status))
        except (ValueError,OSError,http.client.HTTPException) as exc:
            detail={'error':str(exc),'url':job['url']}
            con.execute("UPDATE acquisition_jobs SET status='FETCH_FAILED',attempts=attempts+1,next_attempt=?,detail=? WHERE job_id=?",
                        (time.time()+30*2**job['attempts'],encoded(detail),job['job_id']))
            event(con,'ACQUISITION_FAILED',job['job_id'],detail)
        con.commit()
        done+=1
    return done
