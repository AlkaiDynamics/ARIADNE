import unittest
from dataclasses import replace

from ariadne_core.invariant_detector import (
    CandidateSystem,
    PathSpec,
    Provenance,
    Verdict,
    detect,
)
from ariadne_core.invariant_fixtures import (
    EXPECTED,
    FIXTURES,
    INTEGRITY_EXPECTED,
    MUTATION_EXPECTED,
    MUTATION_INTEGRITY_EXPECTED,
    MUTATIONS,
    POSITIVE_CONTROLS,
    POSITIVE_EXPECTED,
    PREDICATE_MUTATIONS,
    PREDICATE_MUTATION_EXPECTED,
    r_to_s1_calibration,
)


class InvariantDetectorTests(unittest.TestCase):
    def test_fixture_oracle_a0_through_a14(self):
        for fixture_id, candidate in FIXTURES.items():
            with self.subTest(fixture=fixture_id):
                result = detect(candidate)
                self.assertEqual(EXPECTED[fixture_id], result.vector)
                self.assertEqual(INTEGRITY_EXPECTED[fixture_id], result.integrity.verdict.value)

    def test_every_fixture_has_mutation_and_expected_oracle(self):
        self.assertEqual(set(FIXTURES), set(MUTATIONS))
        self.assertEqual(set(FIXTURES), set(MUTATION_EXPECTED))
        for fixture_id, candidate in MUTATIONS.items():
            with self.subTest(mutation=fixture_id):
                result = detect(candidate)
                self.assertEqual(MUTATION_EXPECTED[fixture_id], result.vector)
                self.assertEqual(MUTATION_INTEGRITY_EXPECTED[fixture_id], result.integrity.verdict.value)

    def test_r_to_s1_control_is_core_only_and_sample_scoped(self):
        control = r_to_s1_calibration()
        result = detect(control)
        self.assertIn("sample_scoped", control.name)
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

    def test_partial_lower_level_blocks_higher_pass(self):
        base = FIXTURES["A14"]
        candidate = CandidateSystem(
            name="partial_path_but_later_evidence_present",
            states=base.states,
            projection=base.projection,
            transition=base.transition,
            witness=base.witness,
            path=PathSpec(
                exists=True,
                intermediate_states=base.path.intermediate_states,
                outgoing=base.path.outgoing,
                returning=base.path.returning,
                nd=None,
            ),
            graded=base.graded,
            ch=base.ch,
            across=base.across,
        )
        result = detect(candidate)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kg"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["KCH"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["KA"].verdict)

    def test_missing_core_information_is_incomplete_not_disconfirmation(self):
        base = FIXTURES["A14"]
        candidate = replace(base, name="projection_missing", projection=None)
        result = detect(candidate)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kc"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kg"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["KCH"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["KA"].verdict)

    def test_target_leakage_is_integrity_failure_not_morphology_failure(self):
        result = detect(FIXTURES["A8"])
        self.assertEqual(("PASS", "PASS", "PASS", "PASS", "UNDETERMINED"), result.vector)
        self.assertEqual(Verdict.FAIL, result.integrity.verdict)
        self.assertEqual(("KCH",), result.integrity.target_leakage_levels)
        self.assertEqual((), result.integrity.search_path_leakage_levels)

    def test_search_path_leakage_is_integrity_failure_not_morphology_failure(self):
        result = detect(FIXTURES["A13"])
        self.assertEqual(("PASS", "PASS", "PASS", "PASS", "PASS"), result.vector)
        self.assertEqual(Verdict.FAIL, result.integrity.verdict)
        self.assertEqual((), result.integrity.target_leakage_levels)
        self.assertEqual(("KA",), result.integrity.search_path_leakage_levels)

    def test_leakage_does_not_poison_identical_morphology(self):
        clean = FIXTURES["A14"]
        leaked = replace(
            clean,
            name="same_morphology_target_leaked",
            provenance={"KCH": Provenance(target_leakage=True)},
        )
        self.assertEqual(detect(clean).vector, detect(leaked).vector)
        self.assertEqual(Verdict.PASS, detect(clean).integrity.verdict)
        self.assertEqual(Verdict.FAIL, detect(leaked).integrity.verdict)

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

    def test_five_level_specific_positive_controls_do_not_auto_promote(self):
        for control_id, candidate in POSITIVE_CONTROLS.items():
            with self.subTest(control=control_id):
                self.assertEqual(POSITIVE_EXPECTED[control_id], detect(candidate).vector)

    def test_computed_across_control_uses_actual_adapter_maps(self):
        result = detect(POSITIVE_CONTROLS["Pa"])
        self.assertEqual(("PASS", "PASS", "PASS", "PASS", "PASS"), result.vector)
        predicates = result.levels["KA"].predicates
        for key in (
            "target_ch_pass",
            "projection_compatible",
            "transition_compatible",
            "traversal_out_compatible",
            "traversal_return_compatible",
            "label_compatible",
            "holonomy_compatible",
            "ch_compatible",
        ):
            with self.subTest(predicate=key):
                self.assertTrue(predicates[key])

    def test_predicate_isolating_mutations_fail_at_declared_boundary(self):
        for mutation_id, candidate in PREDICATE_MUTATIONS.items():
            with self.subTest(mutation=mutation_id):
                self.assertEqual(PREDICATE_MUTATION_EXPECTED[mutation_id], detect(candidate).vector)

    def test_candidate_name_is_semantically_irrelevant(self):
        base = POSITIVE_CONTROLS["Pa"]
        renamed = replace(base, name="opaque-candidate-9f2")
        self.assertEqual(detect(base).vector, detect(renamed).vector)
        self.assertEqual(detect(base).integrity.verdict, detect(renamed).integrity.verdict)

    def test_state_and_serialization_order_are_semantically_irrelevant(self):
        base = POSITIVE_CONTROLS["Pa"]
        reordered = replace(
            base,
            name="reordered",
            states=tuple(reversed(base.states)),
            path=replace(base.path, intermediate_states=tuple(reversed(base.path.intermediate_states))),
            ch=replace(base.ch, paths=tuple(reversed(base.ch.paths))),
        )
        self.assertEqual(detect(base).vector, detect(reordered).vector)
        self.assertEqual(detect(base).integrity.verdict, detect(reordered).integrity.verdict)


if __name__ == "__main__":
    unittest.main()
