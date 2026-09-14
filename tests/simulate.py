"""Reproducible retrieval/guard ablations, not benchmarks of unimplemented packages.

Run: python tests/simulate.py
Outputs are synthetic and cannot establish historical validity or global optimality.
"""
import contextlib
import io
import json
import random
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_pipeline import PipelineTests


def main():
    rows=[]
    configs=[('BM25 only',['BM25'],False),('Lexical + fuzzy',['BM25','NGRAM_OSA','TFIDF'],False),
             ('Typed only',['TYPED'],False),('Hybrid RRF',['BM25','NGRAM_OSA','TFIDF','TYPED'],False),
             ('Typed + constraints',['TYPED'],True),('Hybrid + constraints',['BM25','NGRAM_OSA','TFIDF','TYPED'],True)]
    for seed in range(12):
        case=PipelineTests();case.setUp()
        try:
            rng=random.Random(seed)
            docs=[('true-a.txt','72 -> 70 + 2 active mediators'),('true-b.txt','12 -> 10 + 2 active outsiders'),
                  ('invalid.txt','72 -> 69 + 2 active mediators'),('factor.txt','12 × 6 -> 72 translators'),
                  ('other.txt','49 -> 48 + 1 withheld')]
            docs += [(f'noise-{i}.txt',f'72 catalog 70 reference 2 shelf {rng.randrange(100000)}') for i in range(15)]
            rng.shuffle(docs)
            for name,text in docs:case.add(name,text)
            case.compile()
            gold={r[0] for r in case.con.execute("SELECT passage_id FROM active_findings WHERE kind='PARTITION'")
                  if (lambda d:d['arithmetic_valid'] and d['residual_count']==2)(json.loads(case.con.execute('SELECT data FROM active_findings WHERE passage_id=?',(r[0],)).fetchone()[0]))}
            for name,channels,guard in configs:
                case.w.config['retrieval_channels']=channels;case.w.config['retrieval_limit']=8
                hits,coverage=case.w.search(dict(text='72 70 2 active mediators',signature='PARTITION:k=2'))
                if guard:
                    hits=[h for h in hits if any(f['kind']=='PARTITION' and (lambda d:d.get('arithmetic_valid') and d.get('residual_count')==2)(json.loads(f['data']))
                          for f in case.con.execute('SELECT kind,data FROM active_findings WHERE passage_id=?',(h['passage_id'],)))]
                found={h['passage_id'] for h in hits}
                rows.append(dict(seed=seed,configuration=name,returned=len(found),recall=len(found&gold)/len(gold),
                                 precision=len(found&gold)/len(found) if found else 0,
                                 wrong_operator_or_invalid=len(found-gold),truncated=coverage['truncated']))
        finally:case.tearDown()
    out=Path(__file__).resolve().parents[1]/'docs/validation';out.mkdir(exist_ok=True,parents=True)
    (out/'simulation.json').write_text(json.dumps(dict(seed_count=12,corpus_size=20,top_k=8,
        scope='Implemented retrieval/constraint ablations; not full six recommendation package benchmarks',rows=rows),indent=2))
    lines=['# Synthetic retrieval simulation','',
           'Twelve seeded input orders, 20 synthetic sources each, top eight retrieval hits. Gold means a valid explicit partition with residual 2; it does not mean historical truth. Channels and local arithmetic/type checks are real implementation calls. The six ablations below test component combinations, not six fully implemented research frameworks.','',
           '| Combination | Mean recall | Mean precision | Mean wrong-type/invalid candidates |','|---|---:|---:|---:|']
    for name,_,_ in configs:
        rr=[r for r in rows if r['configuration']==name]
        mean=lambda k:sum(r[k] for r in rr)/len(rr)
        lines.append(f"| {name} | {mean('recall'):.3f} | {mean('precision'):.3f} | {mean('wrong_operator_or_invalid'):.2f} |")
    lines += ['', 'Interpretation: typed retrieval handles changed cardinalities without textual identity. Guarded outputs are a comparison shortlist; all rejected or undisplayed source records remain in custody. The fixture favors the explicit partition schema and does not evaluate metaphor, morphology, OCR, unknown languages, broader motifs, source truth, large-corpus scaling, or external acquisition. Reordering a small corpus is a reproducibility stressor, not independent evidence about real research performance.','',
              'The six submitted recommendation families are evaluated separately in PIPELINE_DESIGN.md. MCTS/BALD, full e-graphs, d-DNNF, sheaves and neural components have not been benchmarked by this script.']
    (out/'SIMULATION.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':main()
