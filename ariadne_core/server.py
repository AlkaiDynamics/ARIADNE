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


from .dashboard import PAGE, progress_summary, submit_manifest



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
                    progress=progress_summary(con)
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
                self.send(200,encoded(dict(worker=worker,metrics=metrics,progress=progress)))
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
                        result=submit_manifest(con,raw)
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
