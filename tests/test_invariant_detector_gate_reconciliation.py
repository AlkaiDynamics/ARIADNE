import unittest
from dataclasses import replace

from ariadne_core.invariant_detector_v2 import Verdict, detect
from ariadne_core.invariant_fixtures_v2 import FIXTURES


class RevisedPhase1GateRegressionTests(unittest.TestCase):
    """Regression checks for the post-6fbf648 Phase-1 gate."""

    def test_target_leakage_is_integrity_not_morphology(self):
        leaked = detect(FIXTURES["A8"])
        clean = detect(FIXTURES["A9"])
        self.assertEqual(clean.vector, leaked.vector)
        self.assertEqual(Verdict.FAIL, leaked.integrity.overall)

    def test_search_path_leakage_is_integrity_not_morphology(self):
        leaked = detect(FIXTURES["A13"])
        clean = detect(FIXTURES["A14"])
        self.assertEqual(clean.vector, leaked.vector)
        self.assertEqual(Verdict.FAIL, leaked.integrity.overall)

    def test_partial_prerequisite_blocks_higher_pass(self):
        base = FIXTURES["A14"]
        result = detect(replace(base, path=replace(base.path, nd_policy=None)))
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)
        for level in ("Kg", "KCH", "KA"):
            self.assertEqual(Verdict.PASS, result.levels[level].independent_verdict)
            self.assertEqual(Verdict.PARTIAL, result.levels[level].verdict)

    def test_missing_projection_is_incomplete_not_disconfirmed(self):
        base = FIXTURES["A14"]
        result = detect(replace(base, projection=None))
        self.assertEqual(Verdict.PARTIAL, result.levels["Kc"].verdict)

    def test_bare_tagged_copy_cannot_self_certify_nd(self):
        result = detect(FIXTURES["A3"])
        self.assertFalse(result.levels["Kp"].predicates["ND_preregistered_and_nontrivial"])
        self.assertEqual(Verdict.FAIL, result.levels["Kp"].independent_verdict)


if __name__ == "__main__":
    unittest.main()
