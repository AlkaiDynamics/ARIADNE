import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "research-state" / "candidates" / "sri-yantra" / "candidate.json"


class SriYantraQuarantineContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CANDIDATE.read_text(encoding="utf-8"))

    def test_candidate_is_quarantined_outside_keystone(self):
        self.assertEqual("QUARANTINED_POST_GATE", self.contract["status"])
        self.assertFalse(self.contract["keystone_execution"])
        self.assertFalse(self.contract["training_or_example_domain"])
        self.assertFalse(self.contract["admissible_as_K_evidence"])

    def test_prerequisites_are_both_required(self):
        self.assertEqual(
            ["PHASE1_KEYSTONE_FROZEN", "BLIND_DOMAIN_PROTOCOL_FROZEN"],
            self.contract["prerequisites"],
        )

    def test_allowed_computation_order_is_frozen(self):
        self.assertEqual(
            [
                "PHASE1_KEYSTONE_FREEZE",
                "BLIND_DOMAIN_PROTOCOL_FREEZE",
                "SY_ADMISSIBILITY_RECONSTRUCTION",
                "STRICT_FIBER_CARDINALITY",
                "SELECTOR_CONTINUITY_GLOBAL_SECTION",
                "STRICT_FIBER_MONODROMY_IF_WARRANTED",
            ],
            self.contract["execution_order"],
        )
        self.assertEqual(
            ["STRICT_FIBER_CARDINALITY", "SELECTOR_CONTINUITY_GLOBAL_SECTION"],
            self.contract["first_allowed_computations"],
        )

    def test_ambient_monodromy_cannot_be_credited(self):
        monodromy = self.contract["monodromy"]
        self.assertFalse(monodromy["ambient_clp_creditable"])
        self.assertEqual(
            "STRICT_FIBER_REMAINS_MULTIVALUED_OR_GLOBAL_SECTION_FAILS_NONTRIVIALLY",
            monodromy["strict_fiber_monodromy_gate"],
        )

    def test_unique_continuous_selector_is_a_negative_stopping_rule(self):
        self.assertEqual(
            "UNIQUE_CONTINUOUS_GLOBAL_SELECTOR_TERMINATES_MONODROMY_ROUTE_AS_NEGATIVE_RESULT",
            self.contract["monodromy"]["stopping_rule"],
        )


if __name__ == "__main__":
    unittest.main()
