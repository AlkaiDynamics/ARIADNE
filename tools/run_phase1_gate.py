from __future__ import annotations

import json
import sys

from ariadne_core.invariant_detector import detect
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
)


def check_group(name, cases, expected_vectors, expected_integrity=None):
    rows = []
    ok = True
    for case_id, candidate in cases.items():
        result = detect(candidate)
        expected = expected_vectors[case_id]
        vector_ok = result.vector == expected
        integrity_expected = None if expected_integrity is None else expected_integrity[case_id]
        integrity_ok = True if integrity_expected is None else result.integrity.verdict.value == integrity_expected
        ok = ok and vector_ok and integrity_ok
        rows.append(
            {
                "id": case_id,
                "vector": result.vector,
                "expected_vector": expected,
                "vector_ok": vector_ok,
                "integrity": result.integrity.verdict.value,
                "expected_integrity": integrity_expected,
                "integrity_ok": integrity_ok,
            }
        )
    return ok, {"group": name, "cases": rows}


def main() -> int:
    checks = [
        check_group("fixtures", FIXTURES, EXPECTED, INTEGRITY_EXPECTED),
        check_group("mutations", MUTATIONS, MUTATION_EXPECTED, MUTATION_INTEGRITY_EXPECTED),
        check_group("positive_controls", POSITIVE_CONTROLS, POSITIVE_EXPECTED),
        check_group("predicate_mutations", PREDICATE_MUTATIONS, PREDICATE_MUTATION_EXPECTED),
    ]
    ok = all(flag for flag, _ in checks)
    payload = {
        "phase": "phase1-reconciliation-v2",
        "gate_pass": ok,
        "real_domain_search_allowed": False,
        "groups": [body for _, body in checks],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
