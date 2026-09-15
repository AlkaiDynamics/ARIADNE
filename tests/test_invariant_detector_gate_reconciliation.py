import unittest
from dataclasses import replace

from ariadne_core.invariant_detector import CandidateSystem, PathSpec, Provenance, Verdict, detect
from ariadne_core.invariant_fixtures import FIXTURES


class RevisedPhase1GateRegressionTests(unittest.TestCase):
    """RED tests for the post-6fbf648 Phase-1 gate reconciliation.

    These tests intentionally target the old implementation first. They encode
    the revised gate without introducing real-domain material or new theory.
    """

    def test_target_leakage_does_not_change_morphology_vector(self):
        leaked = FIXTURES["A8"]
        clean = replace(leaked, provenance={})
        self.assertEqual(detect(clean).vector, detect(leaked).vector)

    def test_search_path_leakage_does_not_change_morphology_vector(self):
        leaked = FIXTURES["A13"]
        clean = replace(leaked, provenance={})
        self.assertEqual(detect(clean).vector, detect(leaked).vector)

    def test_partial_prerequisite_blocks_higher_pass(self):
        base = FIXTURES["A14"]
        candidate = replace(base, path=replace(base.path, nd=None))
        result = detect(candidate)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["Kg"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["KCH"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["KA"].verdict)

    def test_missing_projection_is_incomplete_not_disconfirmed(self):
        base = FIXTURES["A14"]
        candidate = replace(base, projection=None)
        result = detect(candidate)
        self.assertNotEqual(Verdict.FAIL, result.levels["Kc"].verdict)

    def test_boolean_nd_cannot_certify_a_bare_tagged_copy(self):
        base = FIXTURES["A14"]
        tagged_copy = PathSpec(
            exists=True,
            intermediate_states=tuple(("Y", x) for x in base.states),
            outgoing=lambda x: ("Y", x),
            returning=lambda y: base.transition(y[1]),
            nd=True,
        )
        candidate = replace(base, path=tagged_copy)
        self.assertEqual(Verdict.FAIL, detect(candidate).levels["Kp"].verdict)


if __name__ == "__main__":
    unittest.main()
