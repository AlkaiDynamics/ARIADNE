from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ariadne_core.invariant_detector_v2 import DETECTOR_SPEC_VERSION, detect
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
)


def build_evidence() -> dict:
    fixtures = {}
    fixtures_ok = True
    for fixture_id, candidate in FIXTURES.items():
        result = detect(candidate)
        expected = EXPECTED[fixture_id]
        integrity_expected = INTEGRITY_EXPECTED[fixture_id]
        ok = result.vector == expected and result.integrity.overall.value == integrity_expected
        fixtures_ok &= ok
        fixtures[fixture_id] = {
            "morphology": list(result.vector),
            "independent": list(result.independent_vector),
            "expected": list(expected),
            "integrity": result.integrity.overall.value,
            "integrity_expected": integrity_expected,
            "ok": ok,
        }

    mutations = {}
    mutations_ok = True
    for fixture_id, candidate in MUTATIONS.items():
        result = detect(candidate)
        expected = MUTATION_EXPECTED[fixture_id]
        ok = result.vector == expected
        mutations_ok &= ok
        mutations[fixture_id] = {
            "morphology": list(result.vector),
            "expected": list(expected),
            "ok": ok,
        }

    controls = {}
    controls_ok = True
    for control_id, candidate in POSITIVE_CONTROLS.items():
        result = detect(candidate)
        expected = POSITIVE_EXPECTED[control_id]
        ok = result.vector == expected
        controls_ok &= ok
        controls[control_id] = {
            "morphology": list(result.vector),
            "expected": list(expected),
            "ok": ok,
        }

    predicate_mutations = {}
    predicate_mutations_ok = True
    for mutation_id, candidate in PREDICATE_MUTATIONS.items():
        level, predicate = PREDICATE_MUTATION_ORACLE[mutation_id]
        result = detect(candidate)
        predicates = result.levels[level].predicates
        only_named_false = predicates.get(predicate) is False and all(
            value is True for name, value in predicates.items() if name != predicate
        )
        ok = only_named_false and result.levels[level].independent_verdict.value == "FAIL"
        predicate_mutations_ok &= ok
        predicate_mutations[mutation_id] = {
            "level": level,
            "predicate": predicate,
            "predicates": dict(predicates),
            "ok": ok,
        }

    suite_ok = fixtures_ok and mutations_ok and controls_ok and predicate_mutations_ok
    return {
        "evidence_kind": "KEYSTONE_PHASE1_V2_LOCAL_SYNTHETIC_EVIDENCE",
        "detector_spec_version": DETECTOR_SPEC_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "scope": "synthetic fixtures and verifier controls only",
        "real_domain_search_permitted": False,
        "full_repository_ci": "PENDING",
        "suite_ok": suite_ok,
        "fixtures_ok": fixtures_ok,
        "mutations_ok": mutations_ok,
        "positive_controls_ok": controls_ok,
        "predicate_mutations_ok": predicate_mutations_ok,
        "fixtures": fixtures,
        "paired_mutations": mutations,
        "positive_controls": controls,
        "predicate_mutations": predicate_mutations,
    }


def main() -> int:
    evidence = build_evidence()
    text = json.dumps(evidence, indent=2, sort_keys=True)
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(path)
    else:
        print(text)
    return 0 if evidence["suite_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
