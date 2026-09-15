import unittest

from detector import Verdict, detect
from fixtures import EXPECTED, fixtures, mutations


class KDetectorPhase1Tests(unittest.TestCase):
    def test_A0_to_A14_expected_vectors(self):
        for fixture_id, candidate in fixtures().items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(EXPECTED[fixture_id], detect(candidate).vector)

    def test_monotone_failure_propagation(self):
        for fixture_id, candidate in fixtures().items():
            result = detect(candidate)
            seen_fail = False
            for verdict in result.vector:
                if seen_fail:
                    self.assertEqual(Verdict.FAIL, verdict, fixture_id)
                if verdict == Verdict.FAIL:
                    seen_fail = True

    def test_positive_control_passes_all_levels(self):
        result = detect(fixtures()["A14"])
        self.assertEqual((Verdict.PASS,) * 5, result.vector)
        self.assertFalse(result.integrity_failures)

    def test_target_and_search_leakage_are_independent_rejections(self):
        target = detect(fixtures()["A12"])
        search = detect(fixtures()["A13"])
        self.assertIn("TARGET_LEAKAGE", target.integrity_failures)
        self.assertNotIn("SEARCH_PATH_LEAKAGE", target.integrity_failures)
        self.assertIn("SEARCH_PATH_LEAKAGE", search.integrity_failures)
        self.assertNotIn("TARGET_LEAKAGE", search.integrity_failures)
        self.assertEqual((Verdict.FAIL,) * 5, target.vector)
        self.assertEqual((Verdict.FAIL,) * 5, search.vector)

    def test_single_predicate_mutations_demote_at_expected_boundary(self):
        for name, candidate, expected in mutations():
            with self.subTest(mutation=name):
                self.assertEqual(expected, detect(candidate).vector)


if __name__ == "__main__":
    unittest.main()
