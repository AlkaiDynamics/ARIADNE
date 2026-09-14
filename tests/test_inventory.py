import sqlite3
import unittest

import ariadne
from ariadne_core.federation import register_project
from ariadne_core.history import verify_history
from ariadne_core.inventory import record_git_branch, record_item, record_repository, unclassified
from ariadne_core.store import migrate, verify_events


class FederationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.row_factory=sqlite3.Row
        self.con.executescript(ariadne.SCHEMA)
        migrate(self.con)

    def tearDown(self): self.con.close()

    def test_repository_and_branch_can_exist_without_project_classification(self):
        repo=record_repository(self.con,'example/project')
        branch=record_git_branch(self.con,'example/project','experiment/one',repository_inventory_id=repo)
        rows=unclassified(self.con)
        self.assertEqual(2,len(rows))
        self.assertEqual({'REPOSITORY','GIT_BRANCH'},{r['item_type'] for r in rows})
        self.assertEqual(repo,self.con.execute('SELECT parent_inventory_id FROM federation_inventory WHERE inventory_id=?',(branch,)).fetchone()[0])

    def test_branch_inventory_does_not_create_durable_fork(self):
        record_repository(self.con,'example/project')
        record_git_branch(self.con,'example/project','main')
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM project_forks').fetchone()[0])
        self.assertEqual(0,self.con.execute('SELECT COUNT(*) FROM federation_projects').fetchone()[0])

    def test_inventory_can_be_mapped_later_without_losing_item_identity(self):
        repo=record_repository(self.con,'example/project',status='CLASSIFICATION_PENDING')
        register_project(self.con,'P')
        # A later mapped observation is a new explicit inventory fact; the original
        # unclassified observation remains retained.
        mapped=record_item(self.con,'REPOSITORY','example/project','example/project','OBSERVED','P')
        self.assertNotEqual(repo,mapped)
        self.assertIsNotNone(self.con.execute('SELECT 1 FROM federation_inventory WHERE inventory_id=?',(repo,)).fetchone())
        self.assertEqual('P',self.con.execute('SELECT project_id FROM federation_inventory WHERE inventory_id=?',(mapped,)).fetchone()[0])

    def test_inventory_is_history_and_event_chained(self):
        repo=record_repository(self.con,'zhenrez/K2S0')
        record_git_branch(self.con,'zhenrez/K2S0','dt/3-closeout',repository_inventory_id=repo,
                          detail={'meaning':'not inferred'})
        self.assertTrue(verify_history(self.con))
        self.assertTrue(verify_events(self.con))


if __name__=='__main__': unittest.main()
