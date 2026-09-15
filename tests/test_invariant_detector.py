import unittest

from ariadne_core.invariant_detector import (
    CandidateSystem,
    PathSpec,
    Verdict,
    detect,
)
from ariadne_core.invariant_fixtures import (
    EXPECTED,
    FIXTURES,
    MUTATION_EXPECTED,
    MUTATIONS,
    r_to_s1_calibration,
)


class InvariantDetectorTests(unittest.TestCase):
    def test_fixture_oracle_a0_through_a14(self):
        for fixture_id, candidate in FIXTURES.items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(EXPECTED[fixture_id], detect(candidate).vector)

    def test_every_fixture_has_mutation_and_expected_oracle(self):
        self.assertEqual(set(FIXTURES), set(MUTATIONS))
        self.assertEqual(set(FIXTURES), set(MUTATION_EXPECTED))
        for fixture_id, candidate in MUTATIONS.items():
            with self.subTest(mutation=fixture_id):
                self.assertEqual(MUTATION_EXPECTED[fixture_id], detect(candidate).vector)

    def test_r_to_s1_control_is_core_only(self):
        result = detect(r_to_s1_calibration())
        self.assertEqual(
            ("PASS", "UNDETERMINED", "UNDETERMINED", "UNDETERMINED", "UNDETERMINED"),
            result.vector,
        )

    def test_lower_fail_propagates_upward(self):
        result = detect(FIXTURES["A4"])
        self.assertEqual(Verdict.FAIL, result.levels["Kg"].verdict)
        self.assertEqual(Verdict.FAIL, result.levels["KCH"].verdict)
        self.assertEqual(Verdict.FAIL, result.levels["KA"].verdict)
        self.assertIn("lower-level FAIL propagated upward", result.levels["KCH"].reasons)

    def test_undetermined_lower_level_blocks_higher_pass(self):
        base = FIXTURES["A14"]
        candidate = CandidateSystem(
            name="undetermined_path_but_later_evidence_present",
            states=base.states,
            projection=base.projection,
            transition=base.transition,
            witness=base.witness,
            path=None,
            graded=base.graded,
            ch=base.ch,
            across=base.across,
        )
        result = detect(candidate)
        self.assertEqual(Verdict.UNDETERMINED, result.levels["Kp"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["Kg"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["KCH"].verdict)
        self.assertNotEqual(Verdict.PASS, result.levels["KA"].verdict)

    def test_partial_is_distinct_from_undetermined(self):
        base = FIXTURES["A14"]
        candidate = CandidateSystem(
            name="partial_path",
            states=base.states,
            projection=base.projection,
            transition=base.transition,
            witness=base.witness,
            path=PathSpec(
                exists=True,
                intermediate_states=None,
                outgoing=base.path.outgoing,
                returning=base.path.returning,
                nd=True,
            ),
            graded=None,
            ch=None,
            across=None,
        )
        result = detect(candidate)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)

    def test_target_leakage_rejects_ch_without_poisoning_lower_levels(self):
        result = detect(FIXTURES["A8"])
        self.assertEqual(
            ("PASS", "PASS", "PASS", "FAIL", "FAIL"),
            result.vector,
        )
        self.assertIn("NO_TARGET_LEAKAGE violated", result.levels["KCH"].reasons)

    def test_search_path_leakage_rejects_across_only(self):
        result = detect(FIXTURES["A13"])
        self.assertEqual(
            ("PASS", "PASS", "PASS", "PASS", "FAIL"),
            result.vector,
        )
        self.assertIn("NO_HIDDEN_SEARCH_PATH_LEAKAGE violated", result.levels["KA"].reasons)

    def test_a7_is_rejected_by_null_collision_not_by_discriminativity(self):
        result = detect(FIXTURES["A7"])
        predicates = result.levels["KCH"].predicates
        self.assertTrue(predicates["phi_discriminative"])
        self.assertFalse(predicates["null_collision_small"])

    def test_a14_single_transport_mutation_demotes_only_across(self):
        original = detect(FIXTURES["A14"])
        mutated = detect(MUTATIONS["A14"])
        self.assertEqual(("PASS", "PASS", "PASS", "PASS", "PASS"), original.vector)
        self.assertEqual(("PASS", "PASS", "PASS", "PASS", "FAIL"), mutated.vector)


if __name__ == "__main__":
    unittest.main()
