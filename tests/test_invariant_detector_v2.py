import json
import unittest
from dataclasses import replace

from ariadne_core.invariant_detector_v2 import (
    Verdict,
    candidate_from_data,
    candidate_to_data,
    detect,
)
from ariadne_core.invariant_fixtures_v2 import (
    EXPECTED,
    FIXTURES,
    INTEGRITY_EXPECTED,
    MUTATIONS,
    MUTATION_EXPECTED,
    POSITIVE_CONTROLS,
    POSITIVE_EXPECTED,
    PREDICATE_MUTATIONS,
    PREDICATE_MUTATION_ORACLE,
    TARGET,
    r_to_s1_sampled_calibration,
)


class InvariantDetectorV2GateTests(unittest.TestCase):
    def test_a0_a14_morphology_oracle(self):
        self.assertEqual({f"A{i}" for i in range(15)}, set(FIXTURES))
        for fixture_id, candidate in FIXTURES.items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(EXPECTED[fixture_id], detect(candidate).vector)

    def test_a0_a14_integrity_oracle_is_separate(self):
        for fixture_id, candidate in FIXTURES.items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(INTEGRITY_EXPECTED[fixture_id], detect(candidate).integrity.overall.value)

    def test_every_fixture_retains_a_paired_mutation(self):
        self.assertEqual(set(FIXTURES), set(MUTATIONS))
        self.assertEqual(set(FIXTURES), set(MUTATION_EXPECTED))
        for fixture_id, candidate in MUTATIONS.items():
            with self.subTest(mutation=fixture_id):
                self.assertEqual(MUTATION_EXPECTED[fixture_id], detect(candidate).vector)

    def test_target_leakage_does_not_change_morphology(self):
        leaked = detect(FIXTURES["A8"])
        clean = detect(FIXTURES["A9"])
        self.assertEqual(clean.vector, leaked.vector)
        self.assertEqual(Verdict.FAIL, leaked.integrity.overall)
        self.assertEqual(Verdict.PASS, clean.integrity.overall)

    def test_search_path_leakage_does_not_change_morphology(self):
        leaked = detect(FIXTURES["A13"])
        clean = detect(FIXTURES["A14"])
        self.assertEqual(clean.vector, leaked.vector)
        self.assertEqual(Verdict.FAIL, leaked.integrity.overall)
        self.assertEqual(Verdict.PASS, clean.integrity.overall)

    def test_missing_nd_is_partial_and_blocks_higher_pass(self):
        base = FIXTURES["A14"]
        candidate = replace(base, path=replace(base.path, nd_policy=None))
        result = detect(candidate)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].independent_verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["Kp"].verdict)
        for level in ("Kg", "KCH", "KA"):
            self.assertEqual(Verdict.PASS, result.levels[level].independent_verdict)
            self.assertEqual(Verdict.PARTIAL, result.levels[level].verdict)
            self.assertTrue(result.levels[level].prerequisite_reasons)

    def test_missing_projection_is_incomplete_not_disconfirmed(self):
        base = FIXTURES["A14"]
        result = detect(replace(base, projection=None))
        self.assertEqual(Verdict.PARTIAL, result.levels["Kc"].verdict)
        self.assertNotEqual(Verdict.FAIL, result.levels["Kc"].verdict)
        self.assertEqual(Verdict.PARTIAL, result.levels["KA"].verdict)

    def test_higher_independent_failure_is_retained_when_prerequisite_unknown(self):
        base = FIXTURES["A14"]
        bad_graded = replace(
            base.graded,
            rho_labels={**base.graded.rho_labels, "return": "0", "gamma": "1"},
        )
        result = detect(replace(base, path=None, graded=bad_graded))
        self.assertEqual(Verdict.UNDETERMINED, result.levels["Kp"].verdict)
        self.assertEqual(Verdict.FAIL, result.levels["Kg"].independent_verdict)
        self.assertEqual(Verdict.FAIL, result.levels["Kg"].verdict)
        self.assertFalse(result.levels["Kg"].prerequisite_reasons)

    def test_bare_tagged_copy_is_rejected_by_versioned_nd(self):
        result = detect(FIXTURES["A3"])
        self.assertEqual(Verdict.FAIL, result.levels["Kp"].independent_verdict)
        self.assertFalse(result.levels["Kp"].predicates["ND_preregistered_and_nontrivial"])

    def test_nd_policy_allows_stationary_states_but_requires_structure_on_moved_states(self):
        base = POSITIVE_CONTROLS["C_KP"]
        states = base.states + ("e4",)
        projection = {**base.projection, "e4": "b2"}
        transition = {**base.transition, "e4": "e4"}
        path = replace(
            base.path,
            intermediate_states=base.path.intermediate_states + ("y4",),
            outgoing={**base.path.outgoing, "e4": "y4"},
            returning={**base.path.returning, "y4": "e4"},
        )
        result = detect(replace(base, states=states, projection=projection, transition=transition, path=path))
        self.assertEqual(Verdict.PASS, result.levels["Kp"].verdict)

    def test_label_composition_is_computed_not_asserted(self):
        base = FIXTURES["A14"]
        graded = replace(
            base.graded,
            rho_labels={**base.graded.rho_labels, "return": "0", "gamma": "0"},
        )
        result = detect(replace(base, graded=graded))
        self.assertTrue(result.levels["Kg"].predicates["local_relational_closure"])
        self.assertFalse(result.levels["Kg"].predicates["rho_respects_composition"])
        self.assertEqual(Verdict.FAIL, result.levels["Kg"].independent_verdict)

    def test_collision_rate_is_computed_from_preregistered_null_pairs(self):
        result = detect(FIXTURES["A7"])
        self.assertTrue(result.levels["KCH"].predicates["Phi_discriminative"])
        self.assertFalse(result.levels["KCH"].predicates["null_collision_small"])
        self.assertEqual(Verdict.FAIL, result.levels["KCH"].independent_verdict)

    def test_across_checks_actual_maps(self):
        result = detect(FIXTURES["A10"])
        self.assertFalse(result.levels["KA"].predicates["projection_commutes"])
        self.assertEqual(Verdict.FAIL, result.levels["KA"].independent_verdict)

    def test_across_preserves_designated_movement_not_just_commuting_square(self):
        result = detect(PREDICATE_MUTATIONS["KA_designated_movement"])
        self.assertTrue(result.levels["KA"].predicates["transition_commutes"])
        self.assertFalse(result.levels["KA"].predicates["designated_movement_preserved"])
        self.assertEqual(Verdict.FAIL, result.levels["KA"].independent_verdict)

    def test_connected_anchor_prevents_unrelated_level_stitching(self):
        base = FIXTURES["A14"]
        result = detect(replace(base, graded=replace(base.graded, anchor_id="unrelated-anchor")))
        self.assertFalse(result.levels["Kg"].predicates["anchor_connected"])
        self.assertEqual(Verdict.FAIL, result.levels["Kg"].independent_verdict)

    def test_all_five_positive_controls_stop_at_their_justified_level(self):
        self.assertEqual(set(POSITIVE_EXPECTED), set(POSITIVE_CONTROLS))
        for control_id, candidate in POSITIVE_CONTROLS.items():
            with self.subTest(control=control_id):
                self.assertEqual(POSITIVE_EXPECTED[control_id], detect(candidate).vector)

    def test_predicate_isolating_mutations_fail_only_the_named_predicate(self):
        for mutation_id, candidate in PREDICATE_MUTATIONS.items():
            with self.subTest(mutation=mutation_id):
                level, predicate = PREDICATE_MUTATION_ORACLE[mutation_id]
                result = detect(candidate)
                predicates = result.levels[level].predicates
                self.assertFalse(predicates[predicate])
                self.assertEqual(Verdict.FAIL, result.levels[level].independent_verdict)
                for name, value in predicates.items():
                    if name != predicate:
                        self.assertTrue(value, f"{mutation_id} unintentionally changed {name}: {value}")

    def test_state_order_permutation_invariance(self):
        base = FIXTURES["A14"]
        permuted = replace(base, states=tuple(reversed(base.states)))
        original = detect(base)
        transformed = detect(permuted)
        self.assertEqual(original.vector, transformed.vector)
        self.assertEqual(original.independent_vector, transformed.independent_vector)
        for level in original.levels:
            self.assertEqual(original.levels[level].predicates, transformed.levels[level].predicates)

    def test_semantics_preserving_renaming_invariance_through_kch(self):
        source = detect(POSITIVE_CONTROLS["C_KCH"])
        renamed = detect(TARGET)
        self.assertEqual(source.vector, renamed.vector)
        self.assertEqual(source.independent_vector, renamed.independent_vector)

    def test_serialization_roundtrip_invariance(self):
        base = FIXTURES["A14"]
        payload = candidate_to_data(base)
        serialized = json.dumps(payload, sort_keys=True)
        restored = candidate_from_data(json.loads(serialized))
        before = detect(base)
        after = detect(restored)
        self.assertEqual(before.vector, after.vector)
        self.assertEqual(before.independent_vector, after.independent_vector)
        self.assertEqual(before.integrity, after.integrity)
        for level in before.levels:
            self.assertEqual(before.levels[level].predicates, after.levels[level].predicates)

    def test_covering_calibration_is_explicitly_sample_scoped(self):
        candidate = r_to_s1_sampled_calibration()
        result = detect(candidate)
        self.assertEqual(
            ("PASS", "UNDETERMINED", "UNDETERMINED", "UNDETERMINED", "UNDETERMINED"),
            result.vector,
        )
        self.assertIn("SAMPLED_ONLY", candidate.scope_note)


if __name__ == "__main__":
    unittest.main()
