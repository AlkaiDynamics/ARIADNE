import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ariadne
from ariadne_core.algorithms import AhoCorasick, anti_unify, minimal_unsat_core, missing_mass, osa_distance
from ariadne_core.engine import Warden
from ariadne_core.history import recover, snapshot, state_at, verify_history
from ariadne_core.report import render
from ariadne_core.store import verify_events
from ariadne_core.structure import extract


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        mapping=dict(ROOT=self.root,DB_DIR=self.root/'db',DB_PATH=self.root/'db/ariadne.sqlite',
                     INBOX_DIR=self.root/'inbox',CUSTODY_DIR=self.root/'custody',
                     ARTIFACTS_DIR=self.root/'artifacts',CONFIG_DIR=self.root/'config',
                     TORCH_CONFIG=self.root/'config/torches.json',REPORT_PATH=self.root/'artifacts/latest_report.html')
        self.patches=[patch.object(ariadne,k,v) for k,v in mapping.items()]
        for p in self.patches:p.start()
        ariadne.ensure_dirs()
        ariadne.TORCH_CONFIG.write_text(json.dumps([dict(torch_id='TORCH-JUDAH',title='Judah',state='BANKED',any_terms=['judah'],all_terms=[],min_hits=1)]))
        ariadne.init_db();self.con=ariadne.connect()
        self.w=Warden(self.con,self.root,dict(query_budget=5,candidate_limit=100,retrieval_limit=20))
        self.con.commit()

    def tearDown(self):
        self.con.close()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def add(self,name,text):
        path=self.root/'inbox'/name;path.write_text(text,encoding='utf-8')
        sid,_,_=ariadne.register_source(path)
        return sid

    def typed(self,name,records,family=None,tradition=None):
        return self.add(name,json.dumps(dict(ariadne_schema=1,source=dict(family=family,tradition=tradition),records=records)))

    def compile(self):
        self.w.compile();self.con.commit()

    def test_custody_survives_inbox_modification(self):
        sid=self.add('a.txt','72 -> 70 + 2 active')
        (self.root/'inbox/a.txt').write_text('replaced')
        self.compile()
        self.assertIn('72',self.con.execute('SELECT text FROM source_profiles WHERE source_id=?',(sid,)).fetchone()[0])

    def test_v0_rows_survive_additive_migration(self):
        self.add('a.txt','70 vs 72 unknown')
        before=[tuple(r) for r in self.con.execute('SELECT * FROM discrepancies')]
        self.compile()
        self.assertEqual(before,[tuple(r) for r in self.con.execute('SELECT * FROM discrepancies')])

    def test_duplicate_feed_does_not_duplicate_source(self):
        self.add('a.txt','same');self.add('b.txt','same');self.compile()
        self.assertEqual(1,self.con.execute('SELECT COUNT(*) FROM sources').fetchone()[0])

    def test_custody_tampering_stops_compilation(self):
        sid=self.add('a.txt','72 -> 70 + 2')
        row=self.con.execute('SELECT custody_path FROM sources WHERE source_id=?',(sid,)).fetchone()
        (self.root/row[0]).write_text('changed')
        with self.assertRaisesRegex(ValueError,'Custody'):self.w.compile()

    def test_operators_never_merge_at_same_count(self):
        self.add('a.txt','72 -> 70 + 2 active\n12 × 6 -> 72')
        self.compile()
        rows=self.con.execute("SELECT kind,signature FROM findings WHERE address='72'").fetchall()
        self.assertEqual({'PARTITION','FACTOR'},{r[0] for r in rows})
        self.assertEqual(2,len({r[1] for r in rows}))

    def test_generalized_partition_and_residual_preserved(self):
        self.add('a.txt','72 -> 70 + 2 active')
        self.add('b.txt','12 -> 10 + 2 active')
        self.compile()
        self.assertEqual(1,self.con.execute('SELECT COUNT(*) FROM rule_proposals').fetchone()[0])
        self.assertEqual(2,self.con.execute("SELECT COUNT(*) FROM findings WHERE kind='PARTITION'").fetchone()[0])

    def test_unknown_residual_function_stays_unknown(self):
        self.assertIsNone(extract('72 -> 70 + 2')[0][3]['residual_function'])

    def test_invalid_arithmetic_fails_kitchen(self):
        self.add('a.txt','72 -> 69 + 2');self.add('b.txt','12 -> 10 + 2')
        self.compile()
        self.assertEqual('FAILED_CONTROL',self.con.execute('SELECT verdict FROM challenges').fetchone()[0])

    def test_same_lineage_is_not_independent(self):
        self.typed('a.json',[dict(kind='partition',full_set=72,displayed_set=70,residual_count=2)],'copied-family','A')
        self.typed('b.json',[dict(kind='partition',full_set=12,displayed_set=10,residual_count=2)],'copied-family','B')
        self.compile()
        check=json.loads(self.con.execute('SELECT checks FROM challenges').fetchone()[0])
        self.assertEqual('FAIL_SHARED_FAMILY',check['source_independence'])

    def test_unrun_controls_are_unknown(self):
        self.add('a.txt','72 -> 70 + 2');self.add('b.txt','12 -> 10 + 2')
        self.compile()
        check=json.loads(self.con.execute('SELECT checks FROM challenges').fetchone()[0])
        self.assertEqual('UNKNOWN_NO_SAMPLING_MODEL',check['null_model'])
        self.assertEqual('UNRESOLVED',self.con.execute('SELECT verdict FROM challenges').fetchone()[0])

    def test_claim_conflict_requires_same_scope(self):
        a=dict(kind='claim',subject='council',predicate='count',value='70',scope='event1')
        self.typed('a.json',[a]);self.typed('b.json',[dict(a,value='72',scope='event2')]);self.compile()
        self.assertEqual(0,self.con.execute("SELECT COUNT(*) FROM proposals WHERE kind='SCOPED_CONFLICT'").fetchone()[0])

    def test_conflicting_environments_and_nogood_retained(self):
        a=dict(kind='claim',subject='council',predicate='count',value='70',scope='event1',exclusive=True)
        self.typed('a.json',[a]);self.typed('b.json',[dict(a,value='72')]);self.compile()
        data=json.loads(self.con.execute("SELECT data FROM proposals WHERE kind='SCOPED_CONFLICT'").fetchone()[0])
        self.assertEqual(2,len(data['environments']));self.assertEqual(1,len(data['nogoods']))

    def test_no_machine_promotion(self):
        self.add('a.txt','72 -> 70 + 2');self.compile()
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("UPDATE findings SET provenance_class='SOURCE_EXPLICIT'")

    def test_all_four_directions_and_budget_retention(self):
        self.add('a.txt','72 -> 70 + 2');result=self.w.run(1)
        self.assertEqual(1,result['executed']);self.assertGreaterEqual(result['pending'],3)
        self.assertEqual(set(('DOWN','SIDEWAYS','ORTHOGONAL','UP')),{r[0] for r in self.con.execute('SELECT direction FROM branches')})

    def test_protected_low_volume_thread_ranked_first(self):
        self.add('a.txt','Judah unknown');self.compile()
        self.assertTrue(self.w.ranked()[0]['protected'])

    def test_same_revision_does_not_loop(self):
        self.add('a.txt','72 -> 70 + 2')
        self.w.run(100);result=self.w.run(100)
        self.assertEqual(0,result['executed'])

    def test_new_evidence_reopens_banked_branches(self):
        self.add('a.txt','72 -> 70 + 2');self.w.run(100);self.con.commit()
        self.add('b.txt','12 -> 10 + 2');self.compile()
        self.assertGreater(len(self.w.ranked(only_due=True)),0)

    def test_down_stays_in_source(self):
        a=self.add('a.txt','72 -> 70 + 2');self.add('b.txt','72 -> 70 + 2 active');self.compile()
        hits,_=self.w.search(dict(text='72',source_id=a),'DOWN')
        self.assertTrue(hits);self.assertEqual({a},{h['source_id'] for h in hits})

    def test_orthogonal_returns_other_operator(self):
        self.add('a.txt','72 -> 70 + 2\n12 × 6 -> 72');self.compile()
        hits,_=self.w.search(dict(text='72',address='72',kind='PARTITION'),'ORTHOGONAL')
        self.assertTrue(hits);self.assertTrue(all('×' in h['text'] for h in hits))

    def test_search_sql_metacharacters_are_data(self):
        self.add('a.txt','Judah and a translator');self.compile()
        self.w.search('"; DROP TABLE sources; --')
        self.assertEqual(1,self.con.execute('SELECT COUNT(*) FROM sources').fetchone()[0])

    def test_unicode_and_aho_boundaries(self):
        matcher=AhoCorasick(['salwā','70','angel'])
        self.assertEqual(['salwā'],matcher.find('SALWA\u0304 170 angelic'))

    def test_cap_does_not_claim_saturation(self):
        self.add('a.txt','72 -> 70 + 2\n72 -> 60 + 12\n72 -> 71 + 1');self.compile()
        self.w.config['retrieval_limit']=1
        _,coverage=self.w.search('72')
        self.assertTrue(coverage['truncated']);self.assertEqual('UNKNOWN_OPEN_WORLD',coverage['coverage'])

    def test_history_chain_replay_and_snapshot_recovery(self):
        self.add('a.txt','Judah 72 -> 70 + 2');self.w.run(2);self.con.commit()
        self.assertTrue(verify_history(self.con));self.assertTrue(verify_events(self.con))
        head=self.con.execute('SELECT MAX(revision) FROM state_versions').fetchone()[0]
        replay=state_at(self.con,head)
        for table,rows in replay.items():
            actual=[dict(r) for r in self.con.execute(f'SELECT * FROM "{table}"')]
            self.assertEqual(sorted(map(lambda x:json.dumps(x,sort_keys=True),actual)),sorted(map(lambda x:json.dumps(x,sort_keys=True),rows)),table)
        path=snapshot(self.con,self.root);target=self.root/'recovered.sqlite';recover(path,target)
        with contextlib.closing(sqlite3.connect(target)) as restored:
            self.assertEqual(self.con.execute('SELECT COUNT(*) FROM branches').fetchone()[0],restored.execute('SELECT COUNT(*) FROM branches').fetchone()[0])
        with self.assertRaises(ValueError):recover(path,target)

    def test_crash_rollback_keeps_last_committed_state(self):
        self.add('a.txt','72 -> 70 + 2');self.compile()
        before=self.con.execute('SELECT MAX(revision) FROM state_versions').fetchone()[0]
        self.w.run(2);self.con.rollback()
        self.assertEqual(before,self.con.execute('SELECT MAX(revision) FROM state_versions').fetchone()[0])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM query_runs').fetchone()[0])

    def test_history_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):self.con.execute('DELETE FROM state_versions')

    def test_bad_record_preserved_as_gap(self):
        self.typed('a.json',[dict(kind='partition',full_set='72')]);self.compile()
        self.assertEqual(1,self.con.execute("SELECT COUNT(*) FROM findings WHERE kind='EXTRACTION_GAP'").fetchone()[0])

    def test_multiscale_preserves_members_and_proportions(self):
        self.add('a.txt','72 -> 70 + 2');self.add('b.txt','36 -> 35 + 1');self.compile()
        rows=self.con.execute('SELECT * FROM scale_patterns WHERE level=1').fetchall()
        self.assertEqual(1,len(rows));self.assertEqual(2,len(json.loads(rows[0]['members'])))

    def test_html_escapes_source_markup_and_shows_all(self):
        self.add('a.txt','<script>alert(1)</script> unknown');self.compile();path=render(self.w)
        content=path.read_text();self.assertNotIn('<script>alert',content);self.assertIn('Show all retained branches',content)

    def test_watch_runs_repeatedly_without_agents(self):
        self.con.commit()
        from warden import watch
        self.add('a.txt','72 -> 70 + 2')
        with contextlib.redirect_stdout(io.StringIO()):watch(interval=.001,budget=2,cycles=3)
        self.assertTrue((self.root/'artifacts/watch_status.json').exists())
        self.assertNotEqual('ERROR_RETRY',json.loads((self.root/'artifacts/watch_status.json').read_text())['status'])
        self.assertGreater(self.con.execute('SELECT COUNT(*) FROM query_runs').fetchone()[0],0)

    def test_os_lock_prevents_second_writer(self):
        from warden import single_writer
        with single_writer(self.root):
            with self.assertRaises(RuntimeError):
                with single_writer(self.root):pass

    def test_chat_guidance_cannot_support_connections(self):
        self.add('chat.txt','User: 72 -> 70 + 2 active\nAssistant: Judah')
        self.add('source.txt','12 -> 10 + 2 active');self.compile()
        self.assertEqual(1,self.con.execute("SELECT COUNT(*) FROM source_lanes WHERE lane='G0'").fetchone()[0])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM proposals').fetchone()[0])
        hits,_=self.w.search('72 Judah')
        self.assertTrue(all(h['lane']=='E0' for h in hits))
        self.assertGreater(self.con.execute('SELECT COUNT(*) FROM branches').fetchone()[0],0)

    def test_twenty_message_checkpoint_is_idempotent_guidance(self):
        from ariadne_core.server import accept_message
        for i in range(20):accept_message(self.con,self.root,str(i),'stream',f'Judah message {i}')
        result=accept_message(self.con,self.root,'19','stream','duplicate retry')
        self.assertEqual(0,result['checkpoints_created'])
        self.assertEqual(1,self.con.execute('SELECT COUNT(*) FROM chat_checkpoints').fetchone()[0])
        self.assertEqual('G0',self.con.execute('SELECT lane FROM source_lanes').fetchone()[0])

    def test_acquisition_raw_custody_and_recursive_pointer(self):
        from ariadne_core.acquisition import queue_manifest,acquire
        queue_manifest(self.con,'https://example.org/a\ndoi:10.1234/example\nhttps://example.org/a')
        def fake(url):return 'FETCHED',b'72 -> 70 + 2\nhttps://example.org/child',dict(url=url,headers={'content-type':'text/plain'})
        self.assertEqual(1,acquire(self.con,self.root,1,fetcher=fake))
        self.compile()
        self.assertEqual(1,self.con.execute("SELECT COUNT(*) FROM acquisition_jobs WHERE status='LINKED'").fetchone()[0])
        self.assertIsNotNone(self.con.execute("SELECT * FROM acquisition_jobs WHERE url='https://example.org/child'").fetchone())
        self.assertTrue(verify_history(self.con))

    def test_failed_acquisition_is_not_absent_evidence(self):
        from ariadne_core.acquisition import queue_manifest,acquire
        queue_manifest(self.con,'https://example.org/blocked')
        acquire(self.con,self.root,1,fetcher=lambda u:('ROBOTS_BLOCKED',None,{'url':u}))
        self.assertEqual('ROBOTS_BLOCKED',self.con.execute('SELECT status FROM acquisition_jobs').fetchone()[0])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM sources').fetchone()[0])

    def test_private_network_acquisition_rejected(self):
        from ariadne_core.acquisition import public_target
        with self.assertRaises(ValueError):public_target('http://127.0.0.1/private')
        with self.assertRaises(ValueError):public_target('file:///etc/passwd')

    def test_multivalue_claims_do_not_create_nogoods(self):
        a=dict(kind='claim',subject='person',predicate='role',value='poet',scope='life')
        self.typed('a.json',[a]);self.typed('b.json',[dict(a,value='teacher')]);self.compile()
        p=self.con.execute('SELECT kind,data FROM proposals').fetchone()
        self.assertEqual('SCOPED_VARIANT',p[0]);self.assertEqual([],json.loads(p[1])['nogoods'])

    def test_recompile_keeps_prior_extraction_out_of_current_view(self):
        self.add('a.txt','72 -> 70 + 2');self.compile()
        old=self.con.execute('SELECT finding_id FROM active_findings').fetchone()[0]
        self.w.implementation_id='test-new-compiler';self.compile()
        self.assertIsNotNone(self.con.execute('SELECT * FROM findings WHERE finding_id=?',(old,)).fetchone())
        self.assertIsNone(self.con.execute('SELECT * FROM active_findings WHERE finding_id=?',(old,)).fetchone())


class AlgorithmTests(unittest.TestCase):
    def test_anti_unification_reuses_variables(self):
        self.assertEqual(('f','?v0','?v0'),anti_unify(('f',1,1),('f',2,2)))

    def test_unsat_core_excludes_irrelevant_clause(self):
        self.assertEqual([0,1],minimal_unsat_core([[1],[-1],[2]]))
        self.assertEqual([],minimal_unsat_core([[1,2],[-1,2]]))

    def test_solver_bound_is_explicit(self):
        with self.assertRaises(ValueError):minimal_unsat_core([[i] for i in range(1,14)])

    def test_missing_mass_no_data_is_unknown(self):
        self.assertIsNone(missing_mass([]));self.assertEqual(.5,missing_mass(['a','b','a','c']))

    def test_transposition(self):
        self.assertEqual(1,osa_distance('shenayim','sheny aim'.replace(' ','')))


if __name__=='__main__':unittest.main()
