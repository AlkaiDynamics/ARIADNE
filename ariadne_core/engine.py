"""Warden orchestration: preserve, compile, reconnect, challenge, explore, bank."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, deque
from pathlib import Path

from . import VERSION
from .algorithms import (AhoCorasick, anti_unify, grams, jaccard, minhash,
                         missing_mass, normalize, osa_distance, pareto_layers,
                         rrf, tfidf_scores, tokens, ucb)
from .store import encoded, event, identity, migrate
from .structure import extract, structured_record

DIRECTIONS = ('DOWN', 'SIDEWAYS', 'ORTHOGONAL', 'UP')
DEFAULTS = dict(query_budget=40, max_depth=3, retrieval_limit=30, candidate_limit=400,
                display_limit=40, stale_rounds=2, novelty_floor=.05,
                near_duplicate_threshold=.85, exploration_weight=.3, diversity_weight=.2,
                protected_torches=['TORCH-JUDAH'], aliases={},
                weights=dict(novelty=.25, diagnostic=.3, torch=.2, coverage_gap=.15, yield_=.1))


class Warden:
    def __init__(self, con, root, config=None):
        self.con, self.root = con, Path(root)
        self.config = dict(DEFAULTS)
        path = self.root/'config/pipeline.json'
        if path.exists():
            self.config.update(json.loads(path.read_text(encoding='utf-8')))
        self.config.update(config or {})
        for k in ('query_budget','max_depth','retrieval_limit','candidate_limit','display_limit','stale_rounds'):
            if type(self.config[k]) is not int or self.config[k] < (0 if k in ('max_depth','query_budget') else 1):
                raise ValueError(f'Invalid nonnegative integer setting: {k}')
        for k in ('novelty_floor','near_duplicate_threshold','exploration_weight','diversity_weight'):
            if not isinstance(self.config[k], (int,float)) or not math.isfinite(self.config[k]) or not 0 <= self.config[k] <= 1:
                raise ValueError(f'Invalid [0,1] setting: {k}')
        if not isinstance(self.config['aliases'], dict) or any(not isinstance(k,str) or not isinstance(v,list) or not all(isinstance(x,str) for x in v) for k,v in self.config['aliases'].items()):
            raise ValueError('aliases must map strings to lists of strings')
        if any(not isinstance(v,(float,int)) or not math.isfinite(v) or v < 0 for v in self.config['weights'].values()):
            raise ValueError('weights must be finite and nonnegative')
        migrate(con)
        self.config_hash = identity('CFG', self.config)
        implementation_root = Path(__file__).resolve().parent.parent
        files = {str(p.relative_to(implementation_root)):p.read_text(encoding='utf-8') for p in sorted([*implementation_root.glob('*.py'),*implementation_root.glob('ariadne_core/*.py')])}
        self.implementation_id = identity('IMPL',files)
        con.execute('INSERT OR IGNORE INTO implementation_versions VALUES(?,?)',(self.implementation_id,encoded(files)))

    def edge(self, src, dst, relation, evidence):
        self.con.execute('INSERT OR IGNORE INTO graph_edges VALUES(?,?,?,?,?,?)',
                         (identity('EDGE',src,dst,relation),src,dst,relation,encoded(evidence),VERSION))

    def passage(self, source_id, locator, text):
        pid = identity('P',source_id,locator)
        cursor = self.con.execute('INSERT OR IGNORE INTO passages VALUES(?,?,?,?)', (pid,source_id,locator,text))
        if cursor.rowcount:
            self.con.execute('INSERT INTO passage_fts VALUES(?,?)', (pid,text))
            self.con.executemany('INSERT OR IGNORE INTO gram_index VALUES(?,?)', ((g,pid) for g in sorted(grams(text))))
            self.edge(source_id,pid,'CONTAINS',{'locator':locator})
        return pid

    def finding(self, pid, kind, signature, address, data):
        fid = identity('F',pid,kind,data,self.implementation_id)
        cell = 'AD_SEG' if kind in ('PARTITION','FACTOR','DECODER_SHIFT') else 'COLD_CASE' if kind in ('RESIDUAL','EXTRACTION_GAP') else 'GEN_POP'
        cur = self.con.execute('INSERT OR IGNORE INTO findings VALUES(?,?,?,?,?,?,?,?,?)',
            (fid,pid,kind,signature,address,encoded(data),'MACHINE_PREDICTION',cell,self.implementation_id))
        if cur.rowcount:
            lane=self.con.execute('SELECT lane FROM source_lanes JOIN passages USING(source_id) WHERE passage_id=?',(pid,)).fetchone()
            self.edge(pid,fid,'GUIDANCE_CANDIDATE' if lane and lane[0]=='G0' else 'EXTRACTED_CANDIDATE',{'algorithm':VERSION})
            event(self.con,'INTAKE',fid,{'passage':pid,'kind':kind,'cell':cell,'data':data})
        return fid

    def compile(self):
        """Read immutable custody, not mutable inbox. New passes don't rewrite evidence."""
        from ariadne import extract_text
        compiled = 0
        for src in self.con.execute('SELECT * FROM sources ORDER BY source_id').fetchall():
            known = self.con.execute('SELECT compiled_version FROM source_profiles WHERE source_id=?',(src['source_id'],)).fetchone()
            if known and known[0] == self.implementation_id:
                continue
            path = self.root/src['custody_path']
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != src['sha256']:
                event(self.con,'CUSTODY_FAILED',src['source_id'],{'reason':'missing or changed custody bytes'})
                raise ValueError(f"Custody verification failed: {src['source_id']}")
            text, error = extract_text(path)
            metadata, records = {}, []
            if path.suffix.lower() == '.json' and text:
                try:
                    obj = json.loads(text)
                    if isinstance(obj,dict) and obj.get('ariadne_schema') == 1:
                        metadata = obj.get('source',{})
                        records = obj.get('records',[])
                        if not isinstance(metadata,dict) or not isinstance(records,list):
                            raise ValueError('source must be an object and records a list')
                        for key in ('family','tradition','language','witness_class'):
                            if metadata.get(key) is not None and not isinstance(metadata[key],str):
                                raise ValueError(f'{key} must be a string or null')
                except (ValueError, TypeError) as exc:
                    error = str(exc); metadata, records = {}, []
            event(self.con,'DETECTIVE',src['source_id'],{'text_extracted':text is not None,'error':error})
            from .acquisition import infer_lane
            lane,reason=infer_lane(path,text or '')
            self.con.execute('INSERT OR IGNORE INTO source_lanes VALUES(?,?,?)',(src['source_id'],lane,reason))
            self.con.execute('INSERT OR REPLACE INTO source_profiles VALUES(?,?,?,?,?,?,?,?)',
                (src['source_id'],text or '',metadata.get('family'),metadata.get('tradition'),
                 metadata.get('language'),metadata.get('witness_class'),encoded(metadata),self.implementation_id))
            event(self.con,'ADJUDICATOR',src['source_id'],{'metadata':metadata,'qualification':'DECLARED_METADATA_ONLY','unknown_independence':not metadata.get('family')})
            for i,line in enumerate((text or '').splitlines(),1):
                if not line.strip():
                    continue
                pid = self.passage(src['source_id'],f'extracted-line:{i}',line)
                for kind, signature, address, data in extract(line):
                    self.finding(pid,kind,signature,address,data)
            if error:
                pid = self.passage(src['source_id'],'source',error)
                self.finding(pid,'EXTRACTION_GAP','EXTRACTION_GAP',None,{'error':error})
            for i,record in enumerate(records):
                pid = self.passage(src['source_id'],f'json:/records/{i}',encoded(record))
                try:
                    self.finding(pid,*structured_record(record))
                except ValueError as exc:
                    self.finding(pid,'EXTRACTION_GAP','EXTRACTION_GAP',None,{'error':str(exc),'record':record})
            event(self.con,'PROCESSOR',src['source_id'],{'compiled_version':self.implementation_id})
            for stage in (('UNSUPPORTED_FORMAT',) if text is None else ('EXTRACTED','NORMALIZED','INDEXED','LINKED')):
                self.con.execute('UPDATE acquisition_jobs SET status=? WHERE source_id=?',(stage,src['source_id']))
            compiled += 1
        self.match_torches()
        revision = identity('CORPUS',[(r[0],r[1]) for r in self.con.execute('SELECT source_id,sha256 FROM sources ORDER BY source_id')],VERSION,self.implementation_id,
                            [dict(r) for r in self.con.execute('SELECT torch_id,any_terms_json,all_terms_json,min_hits FROM torches ORDER BY torch_id')], self.config_hash)
        prior = self.con.execute("SELECT value FROM pipeline_state WHERE key='revision'").fetchone()
        if not prior or prior[0] != revision:
            self.con.execute("UPDATE branches SET status=CASE WHEN depth>? THEN 'DEFERRED' ELSE 'OPEN' END, reason='Corpus, torches, or configuration changed; recheck retained branch'",(self.config['max_depth'],))
            self.con.execute("INSERT OR REPLACE INTO pipeline_state VALUES('revision',?)",(revision,))
            event(self.con,'REOPEN',revision,{'compiled_sources':compiled,'config':self.config})
        self.revision = revision
        for link in self.con.execute('SELECT * FROM acquisition_links ORDER BY parent_id,job_id,relation').fetchall():
            self.edge(link['parent_id'],link['job_id'],link['relation'],{'origin':'acquisition ledger'})
        for job in self.con.execute('SELECT job_id,source_id FROM acquisition_jobs WHERE source_id IS NOT NULL').fetchall():
            self.edge(job['job_id'],job['source_id'],'ACQUIRED_SOURCE',{'job_id':job['job_id']})
        self.reconnect()
        for row in self.con.execute('SELECT finding_id FROM discovery_findings ORDER BY finding_id').fetchall():
            self.spawn(row[0])
        from .fractal import multiscale
        multiscale(self)
        return compiled

    def match_torches(self):
        torches = self.con.execute('SELECT * FROM torches ORDER BY torch_id').fetchall()
        all_terms = {x for t in torches for k in ('any_terms_json','all_terms_json') for x in json.loads(t[k])}
        matcher = AhoCorasick(all_terms)
        for p in self.con.execute('SELECT * FROM passages ORDER BY passage_id').fetchall():
            matches = set(matcher.find(p['text']))
            for t in torches:
                required = set(json.loads(t['all_terms_json']))
                terms = matches & (required | set(json.loads(t['any_terms_json'])))
                if required <= matches and len(terms) >= t['min_hits']:
                    fid = self.finding(p['passage_id'],'TORCH_HIT','TORCH:'+t['torch_id'],None,
                                       {'torch_id':t['torch_id'],'terms':sorted(terms)})
                    self.edge(fid,t['torch_id'],'REIGNITES',{'terms':sorted(terms)})
                    self.con.execute("UPDATE torches SET state='REIGNITED' WHERE torch_id=? AND state='BANKED'",(t['torch_id'],))

    def reconnect(self):
        """Indexed typed joins. Pair output can be quadratic and remains inspectable."""
        pairs = self.con.execute('''SELECT a.finding_id l,b.finding_id r FROM active_findings a JOIN active_findings b
            ON a.signature=b.signature AND a.finding_id<b.finding_id
            WHERE a.kind IN ('PARTITION','FACTOR','CLAIM','DECODER_SHIFT') ORDER BY l,r''')
        for pair in pairs.fetchall():
            left,right = (self.get_finding(pair[k]) for k in ('l','r'))
            # Multiple signals in one source are not cross-source corroboration.
            if left['source_id'] == right['source_id']:
                continue
            a,b = json.loads(left['data']),json.loads(right['data'])
            kind = 'STRUCTURAL_ALIGNMENT'
            if left['kind'] == 'CLAIM':
                if any(a[k] != b[k] for k in ('subject','predicate','scope')) or a['value'] == b['value']:
                    continue
                kind = 'SCOPED_CONFLICT' if a.get('exclusive') is True and b.get('exclusive') is True else 'SCOPED_VARIANT'
            pid = identity('LINK',left['finding_id'],right['finding_id'],kind,VERSION)
            environments = [[f"accept:{left['finding_id']}"],[f"accept:{right['finding_id']}"]]
            data = {'environments':environments,'support':{'AND':[left['finding_id'],right['finding_id']]},
                    'nogoods':[[*environments[0],*environments[1],'assume:declared_predicate_is_exclusive']] if kind == 'SCOPED_CONFLICT' else [],
                    'meaning':'alternative statements retained; formal conflict conditional on matching declared scope'}
            cur = self.con.execute('INSERT OR IGNORE INTO proposals VALUES(?,?,?,?,?,?,?)',
                (pid,left['finding_id'],right['finding_id'],kind,encoded(data),'MACHINE_PREDICTION',VERSION))
            if not cur.rowcount:
                continue
            self.edge(left['finding_id'],right['finding_id'],kind,{'proposal':pid})
            if left['kind'] == 'PARTITION' and a.get('arithmetic_valid') and b.get('arithmetic_valid'):
                expr = anti_unify(('partition',a['full_set'],a['displayed_set'],a['residual_count']),
                                  ('partition',b['full_set'],b['displayed_set'],b['residual_count']))
                self.con.execute('INSERT OR IGNORE INTO rule_proposals VALUES(?,?,?,?,?)',
                    (identity('RULE',pid),encoded([left['finding_id'],right['finding_id']]),encoded(expr),'EXPERIMENTAL',VERSION))
            event(self.con,'GUARDS',pid,data)
            self.kitchen(pid)

    def get_finding(self, fid):
        return self.con.execute('''SELECT f.*,p.source_id,p.locator,p.text,s.family,s.tradition,s.language
          FROM findings f JOIN passages p USING(passage_id) JOIN source_profiles s USING(source_id)
          WHERE f.finding_id=?''',(fid,)).fetchone()

    def kitchen(self, pid):
        proposal = self.con.execute('SELECT * FROM proposals WHERE proposal_id=?',(pid,)).fetchone()
        a,b = (self.get_finding(proposal[k]) for k in ('left_id','right_id'))
        da,db = json.loads(a['data']),json.loads(b['data'])
        similarity = jaccard(grams(a['text']),grams(b['text']))
        independence = 'UNKNOWN'
        if a['family'] and b['family']:
            independence = 'FAIL_SHARED_FAMILY' if a['family'] == b['family'] else 'DISTINCT_DECLARED_FAMILIES'
        arithmetic = 'FAIL' if any(x.get('arithmetic_valid') is False for x in (da,db)) else 'PASS' if all(x.get('arithmetic_valid') is True for x in (da,db)) else 'NOT_APPLICABLE'
        checks = {'arithmetic':arithmetic,'source_independence':independence,
                  'near_duplicate':similarity >= self.config['near_duplicate_threshold'],
                  'text_jaccard':round(similarity,6),'negative_control':'UNKNOWN_NO_LABELLED_CONTROL',
                  'null_model':'UNKNOWN_NO_SAMPLING_MODEL','historical_plausibility':'UNKNOWN',
                  'translation_risk':'UNKNOWN','leave_one_source_out':'FRAGILE_TWO_PREMISES',
                  'interpretation':'challenge results do not certify historical truth'}
        verdict = 'FAILED_CONTROL' if arithmetic == 'FAIL' or independence == 'FAIL_SHARED_FAMILY' or checks['near_duplicate'] else 'UNRESOLVED'
        cid = identity('CHECK',pid,checks,VERSION)
        self.con.execute('INSERT OR IGNORE INTO challenges VALUES(?,?,?,?,?)',(cid,pid,encoded(checks),verdict,VERSION))
        event(self.con,'KITCHEN',pid,{'checks':checks,'verdict':verdict})
        return checks

    def spawn(self, fid, parent='', depth=0):
        f = self.get_finding(fid)
        data = json.loads(f['data'])
        protected = data.get('torch_id') in self.config['protected_torches']
        diagnostic = 1.0 if protected or f['kind'] in ('DISCREPANCY','RESIDUAL','EXTRACTION_GAP') else .6
        for direction in DIRECTIONS:
            # Context belongs in query identity; identical searches share execution,
            # while all origins and return paths survive in branch_origins.
            query = dict(text=' '.join(tokens(f['text'])[:24]), signature=f['signature'],
                         address=f['address'],kind=f['kind'],tradition=f['tradition'],
                         source_id=f['source_id'] if direction == 'DOWN' else None)
            bid = identity('B',direction,query)
            status = 'DEFERRED' if depth > self.config['max_depth'] else 'OPEN'
            self.con.execute('''INSERT INTO branches(branch_id,query,direction,status,depth,protected,diagnostic,torch,reason)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(branch_id) DO UPDATE SET
                depth=min(branches.depth,excluded.depth), protected=max(branches.protected,excluded.protected),
                diagnostic=max(branches.diagnostic,excluded.diagnostic),torch=max(branches.torch,excluded.torch)
                WHERE excluded.depth<branches.depth OR excluded.protected>branches.protected
                OR excluded.diagnostic>branches.diagnostic OR excluded.torch>branches.torch''',
                (bid,encoded(query),direction,status,depth,int(protected),diagnostic,float(f['kind']=='TORCH_HIT'),'Awaiting local search; new corpus or config is a return trigger'))
            cur = self.con.execute('INSERT OR IGNORE INTO branch_origins VALUES(?,?,?)',(bid,fid,parent))
            if cur.rowcount:
                event(self.con,'SPAWN',bid,{'finding':fid,'parent':parent,'direction':direction,'depth':depth})

    def search(self, query, direction='GENERAL'):
        """FTS BM25 + n-gram/OSA + TF-IDF + typed retrieval, fused by RRF."""
        if isinstance(query,str):
            query = {'text':query}
        text = query.get('text','')
        terms = tokens(text)[:24]
        for key,variants in self.config['aliases'].items():
            if normalize(key) in normalize(text):
                terms += [x for v in variants for x in tokens(v)]
        terms = list(dict.fromkeys(terms))[:48]
        cap = self.config['candidate_limit']
        lexical = []
        if terms:
            expression = ' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
            lexical = [r[0] for r in self.con.execute('SELECT passage_id FROM passage_fts WHERE passage_fts MATCH ? ORDER BY bm25(passage_fts),passage_id LIMIT ?', (expression,cap+1))]
        gs = sorted(grams(text))[:80]
        fuzzy = []
        if gs:
            fuzzy = [r[0] for r in self.con.execute('SELECT passage_id FROM gram_index WHERE gram IN ('+','.join('?'*len(gs))+') GROUP BY passage_id ORDER BY COUNT(*) DESC,passage_id LIMIT ?', (*gs,cap+1))]
        structural = []
        if direction == 'DOWN':
            structural = [r[0] for r in self.con.execute('SELECT passage_id FROM passages WHERE source_id=? ORDER BY locator LIMIT ?', (query.get('source_id'),cap+1))]
        elif direction == 'ORTHOGONAL' and query.get('address'):
            structural = [r[0] for r in self.con.execute('SELECT DISTINCT passage_id FROM active_findings WHERE address=? AND kind!=? ORDER BY passage_id LIMIT ?', (query['address'],query['kind'],cap+1))]
        elif query.get('signature'):
            structural = [r[0] for r in self.con.execute('SELECT DISTINCT passage_id FROM active_findings WHERE signature=? ORDER BY passage_id LIMIT ?', (query['signature'],cap+1))]
        if direction == 'UP':
            torch_passages = [r[0] for r in self.con.execute("SELECT DISTINCT passage_id FROM active_findings WHERE kind='TORCH_HIT' ORDER BY passage_id LIMIT ?",(cap+1,))]
            structural = list(dict.fromkeys(structural+torch_passages))
        union = list(dict.fromkeys(structural+lexical+fuzzy))
        truncated = len(union)>cap or any(len(x)>cap for x in (lexical,fuzzy,structural))
        ids = union[:cap]
        if not ids:
            return [],{'candidate_count':0,'truncated':False,'scope':'LOCAL_CORPUS','coverage':'UNKNOWN_OPEN_WORLD'}
        rows = {r['passage_id']:r for r in self.con.execute("SELECT p.*,s.tradition,COALESCE(l.lane,'E0') lane FROM passages p JOIN source_profiles s USING(source_id) LEFT JOIN source_lanes l USING(source_id) WHERE passage_id IN ("+','.join('?'*len(ids))+')',ids)}
        allowed = {i for i in ids if rows[i]['lane']=='E0'}
        if direction == 'DOWN':
            allowed = {i for i in allowed if rows[i]['source_id']==query.get('source_id')}
        elif direction == 'SIDEWAYS':
            # Require same typed class. Unknown traditions remain visible, labelled unknown.
            allowed &= set(structural)
            if query.get('tradition'):
                allowed = {i for i in allowed if rows[i]['tradition'] != query['tradition']}
        elif direction == 'ORTHOGONAL':
            allowed &= set(structural) if query.get('address') else set()
        cosine = tfidf_scores(text,[rows[i]['text'] for i in ids])
        dense_free = [i for i,s in sorted(zip(ids,cosine),key=lambda x:(-x[1],x[0])) if s>0]
        # OSA reranks only bounded short token candidates, never whole long documents.
        fuzzy_scores = {}
        short_query = [t for t in tokens(text)[:12] if 2<=len(t)<=32]
        for i in fuzzy[:cap]:
            if i not in rows:
                continue
            ts = [t for t in tokens(rows[i]['text'])[:48] if len(t)<=32]
            edit = max((1-osa_distance(a,b)/max(len(a),len(b)) for a in short_query for b in ts if abs(len(a)-len(b))<=2),default=0)
            fuzzy_scores[i] = .7*jaccard(grams(text),grams(rows[i]['text']))+.3*edit
        fuzzy_rank = sorted(fuzzy_scores,key=lambda i:(-fuzzy_scores[i],i))
        rankings = [[i for i in rank if i in allowed] for rank in (lexical,fuzzy_rank,dense_free,structural)]
        names=('BM25','NGRAM_OSA','TFIDF','TYPED')
        channels=self.config.get('retrieval_channels',names)
        fused = rrf([rank for name,rank in zip(names,rankings) if name in channels])
        result = []
        for pid,score in fused[:self.config['retrieval_limit']]:
            row = dict(rows[pid]); row['score']=score
            row['channels'] = [name for name,rank in zip(('BM25','NGRAM_OSA','TFIDF','TYPED'),rankings) if pid in rank]
            result.append(row)
        return result,dict(candidate_count=len(ids),matched_count=len(fused),
                           truncated=truncated or len(fused)>self.config['retrieval_limit'],
                           scope='LOCAL_CORPUS',coverage='UNKNOWN_OPEN_WORLD')

    def ranked(self, only_due=False):
        rows = self.con.execute('SELECT * FROM branches ORDER BY branch_id').fetchall()
        active_branches = {r[0] for r in self.con.execute('SELECT DISTINCT branch_id FROM branch_origins JOIN discovery_findings USING(finding_id)')}
        total = sum(r['trials'] for r in rows)
        arms = {d:(sum(r['reward'] for r in rows if r['direction']==d),sum(r['trials'] for r in rows if r['direction']==d)) for d in DIRECTIONS}
        items = []
        for row in rows:
            if only_due and (row['branch_id'] not in active_branches or row['depth']>self.config['max_depth'] or row['last_revision']==self.revision):
                continue
            m = json.loads(row['metrics'])
            item = dict(row); item['id']=row['branch_id']
            item.update(novelty=m.get('novelty',1.0),coverage_gap=1.0 if not row['trials'] else m.get('novelty',1.0),yield_=row['reward']/row['trials'] if row['trials'] else 1.0)
            item['yield']=item['yield_']
            item['utility']=sum(item.get(k,0)*v for k,v in self.config['weights'].items())
            item['ucb']=ucb(*arms[row['direction']],total)
            item['score']=item['utility']+self.config['exploration_weight']*item['ucb']
            items.append(item)
        layers = pareto_layers(items,('novelty','diagnostic','torch','coverage_gap','yield_'))
        selected,seen_directions = [],set()
        while items:
            best = max(items,key=lambda x:(x['protected'],-layers[x['id']],x['score']+self.config['diversity_weight']*(x['direction'] not in seen_directions),x['id']))
            best['pareto_layer']=layers[best['id']]
            selected.append(best); seen_directions.add(best['direction']); items.remove(best)
        return selected

    def run(self, budget=None):
        self.compile()
        budget = self.config['query_budget'] if budget is None else budget
        if type(budget) is not int or budget<0:
            raise ValueError('query budget must be a nonnegative integer')
        event(self.con,'WARDEN',self.revision,{'budget':budget,'config':self.config,'implementation':self.implementation_id,'network':False,'models':False})
        executed = 0
        # Batch allocation amortizes Pareto sorting; rewards update the next batch.
        due = deque(self.ranked(only_due=True))
        for _ in range(budget):
            if not due:
                break
            b = due.popleft()
            query = json.loads(b['query'])
            hits,coverage = self.search(query,b['direction'])
            prior = {r[0] for r in self.con.execute('SELECT DISTINCT passage_id FROM branch_observations WHERE branch_id=?',(b['id'],))}
            fresh = [h for h in hits if h['passage_id'] not in prior]
            novelty = len(fresh)/len(hits) if hits else 0.0
            stale = b['stale']+1 if novelty<=self.config['novelty_floor'] else 0
            for h in hits:
                self.con.execute('INSERT OR IGNORE INTO branch_observations VALUES(?,?,?)',(b['id'],self.revision,h['passage_id']))
                self.edge(b['id'],h['passage_id'],'RETRIEVED',{'revision':self.revision,'channels':h['channels']})
                for f in self.con.execute('SELECT finding_id FROM active_findings WHERE passage_id=?',(h['passage_id'],)).fetchall():
                    self.spawn(f[0],b['id'],b['depth']+1)
            observations = [r[0] for r in self.con.execute('SELECT passage_id FROM branch_observations WHERE branch_id=?',(b['id'],))]
            status = 'PROTECTED' if b['protected'] else 'BANKED'
            reason = 'Local query executed for this corpus revision; new evidence/configuration reopens it'
            if coverage['truncated']:
                status = 'PROTECTED' if b['protected'] else 'DEFERRED'
                reason = 'Retrieval cap reached; results incomplete. Increase limits or refine query; retained for return'
            elif stale >= self.config['stale_rounds']:
                reason = 'Low observed yield across revisions; not a certificate of global saturation'
            metrics = dict(novelty=novelty,duplicate_ratio=1-novelty if hits else None,
                           new_passages=len(fresh),returned=len(hits),singleton_fraction=missing_mass(observations),
                           estimator_validity='DESCRIPTIVE_ONLY_ADAPTIVE_NON_IID',**coverage)
            self.con.execute('UPDATE branches SET status=?,trials=trials+1,reward=reward+?,stale=?,last_revision=?,metrics=?,reason=? WHERE branch_id=?',
                (status,novelty,stale,self.revision,encoded(metrics),reason,b['id']))
            run_id = identity('RUN',b['id'],self.revision)
            result = dict(hits=hits,metrics=metrics,score=b['score'],pareto_layer=b['pareto_layer'])
            self.con.execute('INSERT OR IGNORE INTO query_runs VALUES(?,?,?,?,?)',(run_id,b['id'],self.revision,encoded(result),VERSION))
            event(self.con,'SEARCH',b['id'],result)
            executed += 1
        remaining = len(self.ranked(only_due=True))
        event(self.con,'BANK',self.revision,{'executed':executed,'pending':remaining,'stop':'QUERY_BUDGET' if remaining else 'LOCAL_FRONTIER_EXECUTED','global_completion':False})
        return dict(executed=executed,pending=remaining,revision=self.revision)

    def trace(self, node, hops=4, limit=200):
        """Typed bidirectional BFS with explicit bounds and retained return edges."""
        if hops<0 or limit<1:
            raise ValueError('invalid trace bounds')
        q,seen,edges = deque([(node,0)]),{node},[]
        while q and len(edges)<limit:
            key,depth = q.popleft()
            if depth>=hops:
                continue
            for e in self.con.execute('SELECT * FROM graph_edges WHERE src=? OR dst=? ORDER BY edge_id',(key,key)):
                if len(edges)>=limit:
                    break
                if e['edge_id'] not in {x['edge_id'] for x in edges}:
                    edges.append(dict(e))
                for other in (e['src'],e['dst']):
                    if other not in seen:
                        seen.add(other);q.append((other,depth+1))
        return dict(node=node,edges=edges,bounded=True,max_hops=hops,max_edges=limit)
