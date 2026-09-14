"""Small local feed dashboard and read-only progress projections."""
import json
from .acquisition import pointers, queue_manifest

ATTENTION = ('AUTH_REQUIRED', 'PAYWALLED', 'ROBOTS_BLOCKED',
             'UNSUPPORTED_FORMAT', 'BANKED_DEPTH')


def submit_manifest(con, text):
    if not isinstance(text, str):
        raise ValueError('Paste a resource list as text')
    before = con.execute('SELECT COUNT(*) FROM acquisition_jobs').fetchone()[0]
    detected = len(pointers(text))
    queue_manifest(con, text)
    added = con.execute('SELECT COUNT(*) FROM acquisition_jobs').fetchone()[0] - before
    return dict(queued=added, detected=detected, existing=detected-added)


def progress_summary(con):
    """Counts describe persisted work, never a percentage of total knowledge."""
    counts = {r[0]: r[1] for r in con.execute(
        'SELECT status,COUNT(*) FROM acquisition_jobs GROUP BY status')}
    sources = con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
    indexed = con.execute('SELECT COUNT(DISTINCT p.source_id) FROM passages p JOIN sources s USING(source_id) WHERE s.text_extracted=1').fetchone()[0]
    gaps = con.execute('SELECT COUNT(*) FROM sources WHERE text_extracted=0').fetchone()[0]
    pending = con.execute("""SELECT COUNT(*) FROM acquisition_jobs
        WHERE status='QUEUED' OR (status='FETCH_FAILED' AND attempts<3)""").fetchone()[0]
    failed = con.execute("""SELECT COUNT(*) FROM acquisition_jobs
        WHERE status='FETCH_FAILED' AND attempts>=3""").fetchone()[0]
    # Extraction gaps can also appear as UNSUPPORTED_FORMAT jobs. Keep the two
    # units separate instead of double-counting them as one "items" total.
    attention_jobs = failed + sum(counts.get(s, 0) for s in ATTENTION)
    jobs = []
    for r in con.execute("""SELECT url,status,attempts,detail FROM acquisition_jobs
        WHERE status IN ('FETCH_FAILED','AUTH_REQUIRED','PAYWALLED','ROBOTS_BLOCKED',
                         'UNSUPPORTED_FORMAT','BANKED_DEPTH')
        ORDER BY CASE WHEN status='FETCH_FAILED' AND attempts<3 THEN 1 ELSE 0 END,
                 rowid DESC LIMIT 8"""):
        try:
            detail = json.loads(r['detail'])
        except (ValueError, TypeError):
            detail = {}
        if not isinstance(detail, dict):
            detail = {}
        jobs.append(dict(url=r['url'], status=r['status'], attempts=r['attempts'],
                         reason=detail.get('error') or detail.get('reason') or '',
                         retrying=r['status']=='FETCH_FAILED' and r['attempts']<3))
    recent = [dict(r) for r in con.execute("""SELECT s.original_name,s.text_extracted,
        s.source_id,(s.text_extracted=1 AND EXISTS(SELECT 1 FROM passages p WHERE p.source_id=s.source_id)) AS indexed
        FROM sources s ORDER BY s.created_at DESC,s.rowid DESC LIMIT 8""")]
    return dict(sources=sources, indexed=indexed, extraction_gaps=gaps,
                queued=pending, attention_jobs=attention_jobs,
                acquired=sum(counts.get(s, 0) for s in
                             ('CUSTODIED','EXTRACTED','NORMALIZED','INDEXED','LINKED','UNSUPPORTED_FORMAT')),
                linked=counts.get('LINKED',0), total_pointers=sum(counts.values()),
                statuses=counts, jobs=jobs, recent=recent,
                findings=con.execute('SELECT COUNT(*) FROM active_findings').fetchone()[0],
                revision=con.execute('SELECT COALESCE(MAX(revision),0) FROM state_versions').fetchone()[0])


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARIADNE · Research inbox</title>
<style>
:root{color-scheme:dark;--bg:#111720;--panel:#1b2531;--line:#3d4e5e;--text:#edf3f8;--muted:#b4c2d0;--accent:#a5e4cd}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
main{max-width:640px;margin:40px auto;padding:0 20px 30px}header{display:flex;align-items:center;justify-content:space-between;gap:15px}
h1{font-size:23px;letter-spacing:.1em;margin:0}h2{font-size:15px;margin:0 0 8px}.muted,small{color:var(--muted)}
#status{font-size:13px;color:var(--accent)}#drop{display:block;width:100%;border:1px dashed var(--accent);background:var(--panel);color:var(--text);border-radius:12px;padding:27px 15px;margin:22px 0 16px;cursor:pointer}
#drop strong{display:block;font-size:18px}#drop span{display:block;margin-top:5px;color:var(--muted)}
#drop.over{background:#253c3b}button,textarea,input{font:inherit}button:disabled{opacity:.65;cursor:wait}
textarea{width:100%;min-height:96px;resize:vertical;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;color:var(--text);margin-top:7px}
button.primary{background:var(--accent);color:#102b24;border:0;border-radius:7px;padding:9px 15px;cursor:pointer}
.actions{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:8px}a{color:var(--accent)}
button:focus-visible,textarea:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid #ffe4a2;outline-offset:4px}
#message{white-space:pre-wrap;font-size:13px;max-height:120px;overflow:auto}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:23px}
.card{background:var(--panel);padding:12px 8px;border-radius:8px;text-align:center}.card strong{display:block;font-size:25px}.card span{font-size:12px;color:var(--muted)}
#progress,#updated{font-size:12px;color:var(--muted)}details{border-top:1px solid var(--line);padding-top:12px;margin-top:14px}summary{cursor:pointer}
ul{padding-left:18px}li{margin:9px 0;overflow-wrap:anywhere}.tag{color:var(--accent);font-size:12px;display:block}
#problems:empty::before{content:"No acquisition problems recorded."}#recent:empty::before{content:"Your preserved sources will appear here."}
@media(max-width:420px){main{margin-top:24px;padding:0 14px 24px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head><body><main>
<header><h1>ARIADNE</h1><span id="status" role="status">Connecting…</span></header>
<p class="muted">Your research inbox. Drop resources. Follow progress.</p>
<button id="drop" type="button"><strong>Drop files here</strong><span>or click to choose · papers, notes, resource lists</span></button>
<input id="files" type="file" multiple hidden>
<label for="manifest">Or paste links and resource lists</label>
<textarea id="manifest" placeholder="Web links, DOIs, arXiv IDs, or a list copied from your browser"></textarea>
<div class="actions"><button class="primary" id="acquire" type="button">Fetch resources</button><a href="/report" target="_blank" rel="noopener">View findings ↗</a></div>
<p id="message" role="status" aria-live="polite"></p>
<div class="cards">
<div class="card"><strong id="queued">—</strong><span>Queued links</span></div>
<div class="card"><strong id="sources">—</strong><span>Sources saved</span></div>
<div class="card"><strong id="indexed">—</strong><span>Sources indexed</span></div>
<div class="card"><strong id="findings">—</strong><span>Candidate findings</span></div>
</div>
<p id="progress">Waiting for the first status update.</p>
<details id="attention"><summary id="attention-label">Needs attention</summary><ul id="problems"></ul></details>
<details><summary>Recent sources</summary><ul id="recent"></ul><a href="/report" target="_blank" rel="noopener">All sources and return paths ↗</a></details>
<details><summary>Options &amp; help</summary>
<p>Drop a text or Markdown resource list, or a browser bookmarks HTML export. Explicit links are queued automatically. A title without a link is kept, but needs a resolvable URL or DOI.</p>
<label>Chat export (research guidance) <input id="guidance" type="file" multiple></label>
<p>Chat guidance can suggest searches; it cannot support evidence claims. Machine findings remain candidates.</p>
<p>Files are limited to 25 MiB each. Text PDFs need Poppler; scanned pages need OCR. Originals are preserved when extraction is unavailable.</p>
<p>Keep ARIADNE and your computer running. You may close this browser tab; the local worker continues. Restarting ARIADNE resumes stored work.</p>
</details><p id="updated"></p>
</main><script>
const token='__TOKEN__';
const el=id=>document.getElementById(id);
function notice(text){el('message').textContent=text}
async function post(path,data){
 const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-ARIADNE-Token':token},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;
}
let uploading=false;
async function upload(files,lane='AUTO'){
 if(uploading){notice('Please wait for the current upload to finish, then drop these files again.');return}
 const batch=Array.from(files);if(!batch.length)return;
 uploading=true;el('drop').disabled=true;let saved=0;const failures=[];
 try{
  for(const [i,file] of batch.entries()){
   notice('Uploading '+(i+1)+' of '+batch.length+': '+file.name);
   try{
    if(file.size>25*1024*1024)throw Error('exceeds the 25 MiB limit');
    const bytes=new Uint8Array(await file.arrayBuffer());let raw='';
    for(let j=0;j<bytes.length;j+=8192)raw+=String.fromCharCode(...bytes.subarray(j,j+8192));
    await post('/api/upload',{name:file.name,data:btoa(raw),lane});saved++;
   }catch(error){failures.push(file.name+': '+error.message)}
  }
  notice(saved+' of '+batch.length+' files queued for processing.'+(failures.length?'\n'+failures.join('\n'):''));
 }finally{uploading=false;el('drop').disabled=false;el('files').value='';el('guidance').value='';refresh()}
}
el('drop').onclick=()=>el('files').click();
el('files').onchange=event=>upload(event.target.files);
el('guidance').onchange=event=>upload(event.target.files,'G0');
const drop=el('drop');
drop.ondragover=event=>{event.preventDefault();drop.classList.add('over')};
drop.ondragleave=()=>drop.classList.remove('over');
drop.ondrop=event=>{
 event.preventDefault();drop.classList.remove('over');
 if(event.dataTransfer.files.length){upload(event.dataTransfer.files);return}
 const text=event.dataTransfer.getData('text/uri-list')||event.dataTransfer.getData('text/plain');
 if(text){el('manifest').value=text;notice('Link ready. Choose Fetch resources.')}
};
el('acquire').onclick=async()=>{
 const text=el('manifest').value;if(!text.trim()){notice('Paste a link or resource list first.');return}
 el('acquire').disabled=true;
 try{const result=await post('/api/acquire',{text});
  notice(result.detected?result.queued+' new links queued; '+result.existing+' already recorded.':'List saved. No resolvable links found; add URLs, DOIs, or arXiv IDs.');
 }catch(error){notice(error.message)}finally{el('acquire').disabled=false;refresh()}
};
let refreshing=false;
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const response=await fetch('/api/status');if(!response.ok)throw Error('Status unavailable');
  const data=await response.json(),p=data.progress;
  const labels={WAITING:'Watching inbox',PROCESSING:'Processing',ERROR_RETRY:'Retrying after error',STARTING:'Starting'};
  el('status').textContent=labels[data.worker.status]||data.worker.status;
  for(const key of ['queued','sources','indexed','findings'])el(key).textContent=p[key];
  el('progress').textContent=p.acquired+' of '+p.total_pointers+' known links acquired · '+p.linked+' linked to the graph. These counts describe recorded work, not total research coverage.';
  el('attention-label').textContent='Needs attention · '+p.attention_jobs+' links · '+p.extraction_gaps+' extraction gaps';
  const problems=el('problems');problems.replaceChildren();
  if(data.worker.error){const li=document.createElement('li');li.textContent='Worker: '+data.worker.error;problems.append(li)}
  for(const job of p.jobs){const li=document.createElement('li');li.textContent=job.url;
   const tag=document.createElement('span');tag.className='tag';tag.textContent=(job.retrying?'Retry scheduled':job.status.replaceAll('_',' '))+(job.reason?' · '+job.reason:'');li.append(tag);problems.append(li)}
  if(p.extraction_gaps){const li=document.createElement('li');li.textContent=p.extraction_gaps+' originals preserved with extraction gaps. See View findings for details.';problems.append(li)}
  const recent=el('recent');recent.replaceChildren();
  for(const source of p.recent){const li=document.createElement('li');li.textContent=source.original_name;
   const tag=document.createElement('span');tag.className='tag';tag.textContent=source.indexed?'Indexed':source.text_extracted?'Awaiting indexing':'Saved · extraction unavailable';li.append(tag);recent.append(li)}
  el('updated').textContent='Updated '+new Date().toLocaleTimeString()+' · saved state '+p.revision;
 }catch(error){el('status').textContent='Connection lost';el('updated').textContent='Showing the last received counts. Reconnect to update.'}
 finally{refreshing=false}
}
refresh();setInterval(refresh,5000);
</script></body></html>'''
