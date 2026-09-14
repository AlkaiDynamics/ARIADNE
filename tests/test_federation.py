import sqlite3
import unittest

import ariadne
from ariadne_core.federation import (
    create_fork, create_handoff, observe_repository, record_validation,
    register_project, relate_projects, set_fork_status,
)
from ariadne_core.history import verify_history
from ariadne_core.store import migrate, verify_events


class FederationTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ariadne.SCHEMA)
        migrate(self.con)

    def tearDown(self):
        self.con.close()

    def test_unresolved_project_requires_no_repository_or_parent(self):
        register_project(self.con,'BEANS',name='Beginning to End Architectural Navigation System')
        row=self.con.execute("SELECT * FROM federation_projects WHERE project_id='BEANS'").fetchone()
        self.assertEqual('CLASSIFICATION_PENDING',row['status'])
        self.assertEqual('UNRESOLVED',row['role'])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM federation_project_relations').fetchone()[0])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM federation_repository_observations').fetchone()[0])

    def test_repository_observation_does_not_define_project_identity(self):
        register_project(self.con,'K2S0',aliases=['DT-Seed'])
        oid=observe_repository(self.con,'K2S0','zhenrez/K2S0')
        row=self.con.execute('SELECT * FROM federation_repository_observations WHERE observation_id=?',(oid,)).fetchone()
        self.assertEqual('K2S0',row['project_id'])
        self.assertEqual('zhenrez/K2S0',row['repository'])
        self.assertEqual('OBSERVED',row['observation_status'])
        self.assertEqual('DT-Seed',self.con.execute("SELECT alias FROM federation_project_aliases WHERE project_id='K2S0'").fetchone()[0])

    def test_missing_repository_is_recorded_as_unknown_mapping_not_absent_project(self):
        register_project(self.con,'ARGO')
        observe_repository(self.con,'ARGO',None,'NO_MATCH_IN_CURRENT_CENSUS',{'census':'public repositories'})
        self.assertIsNotNone(self.con.execute("SELECT 1 FROM federation_projects WHERE project_id='ARGO'").fetchone())
        self.assertEqual('NO_MATCH_IN_CURRENT_CENSUS',self.con.execute(
            "SELECT observation_status FROM federation_repository_observations WHERE project_id='ARGO'").fetchone()[0])

    def test_durable_fork_is_not_git_branch(self):
        register_project(self.con,'SUN',role='THEORY_MODEL_LINEAGE',status='REGISTERED')
        first=create_fork(self.con,'SUN','MODEL',focus_id='equation',parent_snapshot='sha256:abc',
                          forced_focus='test formal model',fork_id='FORK-SUN-001')
        second=create_fork(self.con,'SUN','EXPERIMENT',focus_id='equation',parent_fork=first,
                           frozen_inputs=['SUN-001'],fork_id='FORK-SUN-002')
        self.assertEqual('FORK-SUN-001',self.con.execute(
            'SELECT parent_fork FROM project_forks WHERE fork_id=?',(second,)).fetchone()[0])
        set_fork_status(self.con,second,'CONTROL',{'reason':'retain as comparison'})
        self.assertEqual('CONTROL',self.con.execute(
            'SELECT status FROM project_forks WHERE fork_id=?',(second,)).fetchone()[0])

    def test_project_relation_requires_explicit_record(self):
        register_project(self.con,'M1')
        register_project(self.con,'ARGO')
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM federation_project_relations').fetchone()[0])
        relate_projects(self.con,'M1','ARGO','BUILDS',status='PROPOSED',evidence={'scope':'design hypothesis'})
        self.assertEqual(1,self.con.execute('SELECT COUNT(*) FROM federation_project_relations').fetchone()[0])

    def test_validation_regimes_are_orthogonal(self):
        record_validation(self.con,'CLAIM','C1','FORMAL','VERIFIED')
        record_validation(self.con,'CLAIM','C1','HISTORICAL_TEXTUAL','HYPOTHESIS')
        rows=self.con.execute("SELECT regime,status FROM validation_records WHERE subject_id='C1' ORDER BY regime").fetchall()
        self.assertEqual([('FORMAL','VERIFIED'),('HISTORICAL_TEXTUAL','HYPOTHESIS')],[(r[0],r[1]) for r in rows])

    def test_handoff_preserves_payload_identity_and_does_not_create_corroboration(self):
        register_project(self.con,'AYLI',status='REGISTERED')
        register_project(self.con,'SUN',status='REGISTERED')
        hid=create_handoff(self.con,'AYLI','SUN','AYLI@abc',['E1-1','E1-2'],
                           epistemic_zones=['E1'],validation_regimes=['HISTORICAL_TEXTUAL'],
                           source_identities={'E1-1':'SRC-1','E1-2':'SRC-2'})
        rows=self.con.execute('SELECT record_id,source_identity FROM federation_handoff_payloads WHERE handoff_id=? ORDER BY record_id',(hid,)).fetchall()
        self.assertEqual([('E1-1','SRC-1'),('E1-2','SRC-2')],[(r[0],r[1]) for r in rows])
        self.assertEqual(0,self.con.execute("SELECT COUNT(*) FROM graph_edges WHERE relation='CORROBORATES'").fetchone()[0])

    def test_federation_state_is_history_chained(self):
        register_project(self.con,'HQ')
        observe_repository(self.con,'HQ','AlkaiDynamics/HQ')
        self.assertTrue(verify_history(self.con))
        self.assertTrue(verify_events(self.con))


if __name__=='__main__':
    unittest.main()
