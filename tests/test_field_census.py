import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ariadne
from ariadne_core.engine import Warden
from ariadne_core.field_census import (ensure_initial_queries, field_map, gate_status,
                                       install, process, register_question)
from ariadne_core.history import install_history


class FieldCensusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        mapping=dict(ROOT=self.root,DB_DIR=self.root/'db',DB_PATH=self.root/'db/ariadne.sqlite',
                     INBOX_DIR=self.root/'inbox',CUSTODY_DIR=self.root/'custody',
                     ARTIFACTS_DIR=self.root/'artifacts',CONFIG_DIR=self.root/'config',
                     TORCH_CONFIG=self.root/'config/torches.json',REPORT_PATH=self.root/'artifacts/latest_report.html')
        self.patches=[patch.object(ariadne,k,v) for k,v in mapping.items()]
        for p in self.patches:p.start()
        ariadne.ensure_dirs();ariadne.TORCH_CONFIG.write_text('[]')
        ariadne.init_db();self.con=ariadne.connect()
        self.w=Warden(self.con,self.root,dict(field_census_required=True,
            field_census_providers=['openalex','crossref','openlibrary'],
            field_census_min_providers=2,field_census_rounds=2,
            field_census_expansion_terms=1,field_census_saturation_novelty=.25))
        install(self.con);install_history(self.con);self.con.commit()

    def tearDown(self):
        self.con.close()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def _attach_result(self, field_query, payload):
        path=self.root/'inbox'/(field_query['provider']+'-'+field_query['field_query_id']+'.json')
        path.write_text(json.dumps(payload),encoding='utf-8')
        sid,_,_=ariadne.register_source(path,connection=self.con)
        self.con.execute("UPDATE acquisition_jobs SET source_id=?,status='CUSTODIED' WHERE job_id=?",
                         (sid,field_query['job_id']))
        return sid

    def _payload(self, provider):
        if provider=='openalex':
            return {'results':[{'id':'https://openalex.org/W1','display_name':'Closure and register change',
                'publication_year':2024,'type':'article','doi':'https://doi.org/10.1/example',
                'cited_by_count':20,'authorships':[{'author':{'display_name':'Ada Author'}}],
                'primary_topic':{'display_name':'Music theory'},'topics':[]}]}
        if provider=='crossref':
            return {'message':{'items':[{'DOI':'10.1/example','title':['Closure and register change'],
                'type':'journal-article','URL':'https://doi.org/10.1/example','is-referenced-by-count':20,
                'author':[{'given':'Ada','family':'Author'}],'subject':['Music theory'],
                'issued':{'date-parts':[[2024]]}}]}}
        return {'docs':[{'key':'/works/OL1W','title':'Closure and register change',
            'author_name':['Ada Author'],'first_publish_year':2024,'subject':['Music theory']}]}

    def test_question_queues_bounded_multi_provider_census(self):
        qid=register_question(self.con,'Can local closure coexist with global register change?',seed_terms=['comma pump'])
        self.assertEqual(3,ensure_initial_queries(self.con,qid,self.w.config))
        rows=self.con.execute('SELECT provider,round_no FROM field_queries WHERE question_id=?',(qid,)).fetchall()
        self.assertEqual({'openalex','crossref','openlibrary'},{r['provider'] for r in rows})
        self.assertEqual({0},{r['round_no'] for r in rows})
        self.assertTrue(gate_status(self.con,self.w.config)['blocked'])

    def test_two_round_census_opens_gate_and_preserves_field_map(self):
        qid=register_question(self.con,'Can local closure coexist with global register change?',seed_terms=['comma pump'])
        ensure_initial_queries(self.con,qid,self.w.config)
        for row in self.con.execute('SELECT * FROM field_queries WHERE question_id=? AND round_no=0',(qid,)).fetchall():
            self._attach_result(row,self._payload(row['provider']))
        self.assertEqual(3,process(self.con,self.root,self.w.config))
        round_one=self.con.execute('SELECT * FROM field_queries WHERE question_id=? AND round_no=1',(qid,)).fetchall()
        self.assertEqual(3,len(round_one))
        for row in round_one:self._attach_result(row,self._payload(row['provider']))
        self.assertEqual(3,process(self.con,self.root,self.w.config))
        gate=gate_status(self.con,self.w.config)
        self.assertFalse(gate['blocked'])
        self.assertEqual('SATURATED',self.con.execute('SELECT status FROM research_questions WHERE question_id=?',(qid,)).fetchone()[0])
        fmap=field_map(self.con,qid)
        self.assertGreaterEqual(fmap['unique_works'],1)
        self.assertTrue(fmap['top_works'])
        self.assertIn('music',dict(fmap['vocabulary']))
        self.assertEqual({'PRIOR_ART_DISCOVERY_METADATA_ONLY'},
            {r[0] for r in self.con.execute('SELECT DISTINCT evidence_scope FROM field_candidates WHERE question_id=?',(qid,))})
        self.assertEqual({'NONE_FOR_UNDERLYING_HISTORICAL_CLAIMS'},
            {r[0] for r in self.con.execute('SELECT DISTINCT historical_authority FROM field_candidates WHERE question_id=?',(qid,))})


if __name__=='__main__':
    unittest.main()
