"""Local-only feed interface; a single algorithm worker runs in the background."""
import base64
import json
import secrets
import signal
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import ariadne
from .acquisition import MAX_BYTES,queue_manifest
from .store import encoded,event,identity


def accept_message(con,root,message_id,stream,content):
    if not all(isinstance(x,str) and x for x in (message_id,stream,content)):
        raise ValueError('message_id, stream and content are required strings')
    con.execute('INSERT OR IGNORE INTO chat_messages VALUES(?,?,?)',(message_id,stream,content))
    used={m for row in con.execute('SELECT message_ids FROM chat_checkpoints WHERE stream=?',(stream,)) for m in json.loads(row[0])}
    pending=[dict(r) for r in con.execute('SELECT * FROM chat_messages WHERE stream=? ORDER BY rowid',(stream,)) if r['message_id'] not in used]
    count=0
    while len(pending)>=20:
        group,pending=pending[:20],pending[20:]
        ids=[m['message_id'] for m in group];cid=identity('CHECKPOINT',stream,ids)
        path=Path(root)/'inbox'/(cid+'.json')
        path.write_text(encoded(dict(lane='G0',messages=group)),encoding='utf-8')
        sid,_,_=ariadne.register_source(path,connection=con)
        con.execute('INSERT OR IGNORE INTO chat_checkpoints VALUES(?,?,?,?)',(cid,stream,encoded(ids),sid))
        event(con,'G0_CHECKPOINT',cid,dict(source_id=sid,message_ids=ids))
        count+=1
    return dict(checkpoints_created=count,pending_messages=len(pending))


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ARIADNE</title>
<style>body{font:16px/1.5 system-ui;background:#101722;color:#edf3fa;margin:0}main{max-width:1000px;padding:28px;margin:auto}h1{font-size:38px;margin:0}header{display:flex;justify-content:space-between;align-items:center}.sub{color:#b9c8d8}#drop{border:2px dashed #80c8b7;padding:35px;text-align:center;border-radius:14px;margin:28px 0;background:#172431}textarea{box-sizing:border-box;width:100%;min-height:145px;background:#192635;color:white;border:1px solid #53677e;border-radius:8px;padding:14px;font:inherit}button,a.button{display:inline-block;background:#93d5c2;color:#102820;border:0;border-radius:7px;padding:10px 18px;margin:12px 8px 12px 0;font:inherit;cursor:pointer}input{font:inherit}#status{color:#9fe0c9}#message{white-space:pre-wrap}#metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}.metric{padding:16px;background:#1c2a3b;border-radius:10px}.metric strong{display:block;font-size:26px}a{color:#a4e8d5}details{margin-top:22px}</style>
<main><header><h1>ARIADNE</h1><span id="status">STARTING</span></header><p class="sub">Feed material. Inspect findings. Trace why.</p>
<section id="drop" tabindex="0" role="button" aria-label="Choose or drop research files"><strong>DROP FILES HERE</strong><p>PDFs, text, notes, HTML, tables, scans, or chat exports</p><input id="files" type="file" multiple aria-label="Choose files"></section>
<label for="manifest">Paste URLs, DOIs, arXiv IDs, or a whole source list</label><textarea id="manifest" placeholder="https://…&#10;doi:10.…&#10;arXiv:…"></textarea><button id="acquire">Acquire</button><a class="button" href="/report" target="_blank">Findings · Torches · Coverage</a>
<p id="message" role="status"></p><div id="metrics"></div>
<details><summary>Chat guidance and evidence separation</summary><label>Import a chat export explicitly as G0 guidance <input id="guidance" type="file" multiple></label><p>Recognized chat exports and 20-message checkpoints enter G0 guidance. They can generate searches but cannot support evidence connections. Other files enter E0 candidate custody. Verification and corroboration require recorded evidence; the engine does not award E1 or E2 automatically.</p><p>Coverage reports observed local work and acquisition outcomes. Total research coverage is unknown.</p><p>Keep this local process running to continue acquisition and discovery. Ctrl+C stops it safely. Restart resumes from stored state.</p></details></main>
<script>
const token='__TOKEN__';
async function post(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-ARIADNE-Token':token},body:JSON.stringify(data)});const j=await r.json();if(!r.ok)throw Error(j.error||r.status);return j;}
async function upload(files,lane='AUTO'){for(const f of files){try{if(f.size>25*1024*1024)throw Error('File exceeds the current 25 MiB upload bound; original not changed.');const bytes=new Uint8Array(await f.arrayBuffer());let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));await post('/api/upload',{name:f.name,data:btoa(s),lane});document.querySelector('#message').textContent='Queued: '+f.name;}catch(e){document.querySelector('#message').textContent=e.message;}}refresh();}
document.querySelector('#files').onchange=e=>upload(e.target.files);
document.querySelector('#guidance').onchange=e=>upload(e.target.files,'G0');
const drop=document.querySelector('#drop');drop.ondragover=e=>e.preventDefault();drop.ondrop=e=>{e.preventDefault();upload(e.dataTransfer.files)};drop.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();document.querySelector('#files').click()}};
document.querySelector('#acquire').onclick=async()=>{try{let j=await post('/api/acquire',{text:document.querySelector('#manifest').value});document.querySelector('#message').textContent=j.queued+' distinct pointers queued; original manifest retained.';refresh()}catch(e){document.querySelector('#message').textContent=e.message}};
async function refresh(){try{const r=await fetch('/api/status');const j=await r.json();document.querySelector('#status').textContent=j.worker.status;const box=document.querySelector('#metrics');box.replaceChildren();for(const [name,value] of Object.entries(j.metrics)){const d=document.createElement('div');d.className='metric';const n=document.createElement('strong');n.textContent=value;d.append(n,document.createTextNode(name));box.append(d)}}catch(e){document.querySelector('#status').textContent='CONNECTION LOST'}}refresh();setInterval(refresh,5000);
</script></html>'''


def serve(port=8765,interval=10):
    from warden import watch
    if not 1<=port<=65535 or interval<=0:raise ValueError('invalid port or interval')
    stop=threading.Event();mutex=threading.RLock();token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,mime='application/json'):
            data=data.encode() if isinstance(data,str) else data
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def allowed(self):
            return self.headers.get('Host') in (f'127.0.0.1:{port}',f'localhost:{port}')
        def do_GET(self):
            if not self.allowed():self.send(403,'{}');return
            path=urlsplit(self.path).path
            if path=='/':self.send(200,PAGE.replace('__TOKEN__',token),'text/html; charset=utf-8')
            elif path=='/api/status':
                with ariadne.connect() as con:
                    metrics={}
                    for table,label in (('sources','Sources'),('graph_edges','Typed relations'),('active_findings','Current evidence candidates'),('branches','Retained searches')):
                        metrics[label]=con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    for row in con.execute('SELECT status,COUNT(*) FROM acquisition_jobs GROUP BY status'):
                        metrics['Acquisition '+row[0]]=row[1]
                    for row in con.execute('SELECT lane,COUNT(*) FROM source_lanes GROUP BY lane'):
                        metrics[row[0]]=row[1]
                    metrics['Unextracted sources']=con.execute('SELECT COUNT(*) FROM sources WHERE text_extracted=0').fetchone()[0]
                    metrics['Reignited torches']=con.execute("SELECT COUNT(*) FROM torches WHERE state='REIGNITED'").fetchone()[0]
                health=ariadne.ARTIFACTS_DIR/'watch_status.json'
                try:worker=json.loads(health.read_text())
                except (OSError,ValueError):worker=dict(status='STARTING')
                self.send(200,encoded(dict(worker=worker,metrics=metrics)))
            elif path in ('/report','/pipeline_state.json','/neurite_notes.md'):
                name={'/report':'latest_report.html'}.get(path,path.lstrip('/'))
                file=ariadne.ARTIFACTS_DIR/name
                if file.exists():self.send(200,file.read_bytes(),'text/html; charset=utf-8' if path=='/report' else 'text/plain; charset=utf-8')
                else:self.send(200,'The first report will appear after the next processing cycle.','text/plain')
            elif path.startswith('/custody/'):
                from urllib.parse import unquote
                file=(ariadne.ROOT/unquote(path.lstrip('/'))).resolve()
                if file.is_relative_to(ariadne.CUSTODY_DIR.resolve()) and file.is_file():
                    # Serve originals as attachment-like binary, never execute HTML sources.
                    self.send(200,file.read_bytes(),'application/octet-stream')
                else:self.send(404,'{}')
            else:self.send(404,'{}')
        def do_POST(self):
            if not self.allowed() or self.headers.get('X-ARIADNE-Token')!=token:
                self.send(403,'{}');return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=36*1024*1024:raise ValueError('request size out of bounds')
                body=json.loads(self.rfile.read(size))
                with mutex,ariadne.connect() as con:
                    if self.path=='/api/acquire':
                        raw=body['text']
                        if not isinstance(raw,str):raise ValueError('text must be a string')
                        result=dict(queued=queue_manifest(con,raw))
                    elif self.path=='/api/upload':
                        data=base64.b64decode(body['data'],validate=True)
                        if len(data)>MAX_BYTES:raise ValueError('upload exceeds 25 MiB')
                        name=Path(body['name'].replace('\\','/')).name
                        if not name or name in ('.','..'):raise ValueError('invalid file name')
                        target=ariadne.INBOX_DIR/(('chat-' if body.get('lane')=='G0' else '')+secrets.token_hex(4)+'-'+name)
                        temporary=target.with_name(target.name+'.part');temporary.write_bytes(data);temporary.replace(target)
                        result=dict(queued=name)
                    elif self.path=='/api/messages':
                        result=accept_message(con,ariadne.ROOT,body['message_id'],body['stream'],body['content'])
                    else:self.send(404,'{}');return
                self.send(200,encoded(result))
            except sqlite3.Error as exc:self.send(503,encoded(dict(error='Research transaction in progress; retry shortly: '+str(exc))))
            except (ValueError,KeyError,OSError,TypeError) as exc:self.send(400,encoded(dict(error=str(exc))))
    server=HTTPServer(('127.0.0.1',port),Handler);server.timeout=.5
    worker=threading.Thread(target=watch,kwargs=dict(interval=interval,stop_event=stop),daemon=True)
    old={sig:signal.signal(sig,lambda *_:stop.set()) for sig in (signal.SIGINT,signal.SIGTERM)}
    worker.start();print(f'ARIADNE running at http://127.0.0.1:{port}',flush=True)
    try:
        while not stop.is_set():server.handle_request()
    finally:
        stop.set();worker.join(timeout=60);server.server_close()
        for sig,handler in old.items():signal.signal(sig,handler)
