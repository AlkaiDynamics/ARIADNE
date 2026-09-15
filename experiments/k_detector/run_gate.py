from detector import detect
from fixtures import EXPECTED, fixtures, mutations


def main():
    ok = True
    print("A0-A14 phase-1 detector gate")
    for fixture_id, candidate in fixtures().items():
        result = detect(candidate)
        expected = EXPECTED[fixture_id]
        passed = result.vector == expected
        ok &= passed
        print(
            f"{fixture_id:>3}  {tuple(v.value for v in result.vector)}  "
            + ("OK" if passed else "MISMATCH")
        )

    print("\nMutation harness")
    for name, candidate, expected in mutations():
        result = detect(candidate)
        passed = result.vector == expected
        ok &= passed
        print(
            f"{name:<18} {tuple(v.value for v in result.vector)}  "
            + ("OK" if passed else "MISMATCH")
        )

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
