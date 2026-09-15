from __future__ import annotations

import copy
from dataclasses import replace

from detector import (
    AcrossSpec,
    AssumptionProvenance,
    CandidateSystem,
    CHSpec,
    MorphologyDomain,
    SearchProvenance,
    Verdict,
)


ALL_PASS = (Verdict.PASS,) * 5


def _positive_domain(name="source"):
    return MorphologyDomain(
        name=name,
        E=("e0", "e1"),
        B=("b0",),
        pi={"e0": "b0", "e1": "b0"},
        tau={"e0": "e1", "e1": "e0"},
        Y=("y0", "y1"),
        out={"e0": "y0", "e1": "y1"},
        ret={"y0": "e1", "y1": "e0"},
        nd=True,
        paths=("id", "loop", "a", "b", "c"),
        rho={"id": "closed", "loop": "closed", "a": "ra", "b": "rb", "c": "rc"},
        h={"id": 0, "loop": 1, "a": 2, "b": 3, "c": 4},
        gamma="loop",
        identity_path="id",
        ch=CHSpec(
            gamma_a="a",
            gamma_b="b",
            internally_equivalent=False,
            phi={"id": "I", "loop": "L", "a": "R", "b": "R", "c": "Q"},
            phi_fixed_before_observation=True,
            null_collision_probability=0.01,
            max_collision_probability=0.05,
        ),
    )


def _target_domain():
    return MorphologyDomain(
        name="target",
        E=("f0", "f1"),
        B=("c0",),
        pi={"f0": "c0", "f1": "c0"},
        tau={"f0": "f1", "f1": "f0"},
        Y=("z0", "z1"),
        out={"f0": "z0", "f1": "z1"},
        ret={"z0": "f1", "z1": "f0"},
        nd=True,
        paths=("iid", "lloop", "aa", "bb", "cc"),
        rho={"iid": "closed2", "lloop": "closed2", "aa": "rra", "bb": "rrb", "cc": "rrc"},
        h={"iid": 10, "lloop": 11, "aa": 12, "bb": 13, "cc": 14},
        gamma="lloop",
        identity_path="iid",
        ch=CHSpec(
            gamma_a="aa",
            gamma_b="bb",
            internally_equivalent=False,
            phi={"iid": "I2", "lloop": "L2", "aa": "R2", "bb": "R2", "cc": "Q2"},
            phi_fixed_before_observation=True,
            null_collision_probability=0.01,
            max_collision_probability=0.05,
        ),
    )


def positive_candidate(name="A14_positive"):
    source = _positive_domain()
    target = _target_domain()
    across = AcrossSpec(
        target=target,
        AE={"e0": "f0", "e1": "f1"},
        AB={"b0": "c0"},
        AY={"y0": "z0", "y1": "z1"},
        AGamma={"id": "iid", "loop": "lloop", "a": "aa", "b": "bb", "c": "cc"},
        ASrho={"closed": "closed2", "ra": "rra", "rb": "rrb", "rc": "rrc"},
        ASh={0: 10, 1: 11, 2: 12, 3: 13, 4: 14},
    )
    return CandidateSystem(
        name=name,
        domain=source,
        across=across,
        assumption_provenance=AssumptionProvenance(
            entries=("finite synthetic morphology; target feature not encoded by representation choice",),
            target_encoded=False,
        ),
        search_provenance=SearchProvenance(
            entries=(
                "single preregistered representation",
                "single preregistered adapter",
                "fixed stopping rule",
            ),
            all_attempts_logged=True,
            stopping_rule_recorded=True,
        ),
    )


def _clone(name):
    candidate = copy.deepcopy(positive_candidate(name))
    candidate.name = name
    return candidate


def fixtures():
    out = {}

    candidate = _clone("A0_identity_no_hidden_change")
    candidate.domain.tau = {"e0": "e0", "e1": "e1"}
    candidate.domain.ret = {"y0": "e0", "y1": "e1"}
    out["A0"] = candidate

    candidate = _clone("A1_visible_change")
    candidate.domain.B = ("b0", "b1")
    candidate.domain.pi = {"e0": "b0", "e1": "b1"}
    out["A1"] = candidate

    candidate = _clone("A2_trivial_factorization_rejected_by_ND")
    candidate.domain.nd = False
    out["A2"] = candidate

    candidate = _clone("A3_bad_factorization_composition")
    candidate.domain.ret = {"y0": "e0", "y1": "e1"}
    out["A3"] = candidate

    candidate = _clone("A4_no_local_relational_closure")
    candidate.domain.rho = dict(candidate.domain.rho)
    candidate.domain.rho["loop"] = "open"
    out["A4"] = candidate

    candidate = _clone("A5_no_global_displacement")
    candidate.domain.h = dict(candidate.domain.h)
    candidate.domain.h["loop"] = candidate.domain.h["id"]
    out["A5"] = candidate

    candidate = _clone("A6_CH_paths_not_internally_inequivalent")
    candidate.domain.ch = replace(candidate.domain.ch, internally_equivalent=True)
    out["A6"] = candidate

    candidate = _clone("A7_CH_fake_collision_via_nondiscriminative_Phi")
    candidate.domain.ch = replace(
        candidate.domain.ch,
        phi={path: "ONE" for path in candidate.domain.paths},
    )
    out["A7"] = candidate

    candidate = _clone("A8_CH_collision_common_under_null")
    candidate.domain.ch = replace(candidate.domain.ch, null_collision_probability=0.50)
    out["A8"] = candidate

    candidate = _clone("A9_CH_posthoc_realization_map")
    candidate.domain.ch = replace(candidate.domain.ch, phi_fixed_before_observation=False)
    out["A9"] = candidate

    candidate = _clone("A10_ACROSS_projection_does_not_commute")
    candidate.across = replace(candidate.across, AB={"b0": "wrong"})
    out["A10"] = candidate

    candidate = _clone("A11_ACROSS_traversal_does_not_commute")
    candidate.across = replace(candidate.across, AY={"y0": "z1", "y1": "z0"})
    out["A11"] = candidate

    candidate = _clone("A12_target_leakage")
    candidate.assumption_provenance = AssumptionProvenance(
        entries=("representation chosen because it encoded the desired target",),
        target_encoded=True,
    )
    out["A12"] = candidate

    candidate = _clone("A13_hidden_search_path_leakage")
    candidate.search_provenance = SearchProvenance(
        entries=("reported only successful adapter after unlogged search",),
        all_attempts_logged=False,
        stopping_rule_recorded=True,
    )
    out["A13"] = candidate

    out["A14"] = positive_candidate()
    return out


EXPECTED = {
    "A0": (Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A1": (Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A2": (Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A3": (Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A4": (Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A5": (Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A6": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL),
    "A7": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL),
    "A8": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL),
    "A9": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL),
    "A10": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL),
    "A11": (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL),
    "A12": (Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A13": (Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
    "A14": ALL_PASS,
}


def mutations():
    cases = []

    candidate = positive_candidate("M_KC_identity")
    candidate.domain.tau = {"e0": "e0", "e1": "e1"}
    candidate.domain.ret = {"y0": "e0", "y1": "e1"}
    cases.append(("M_KC_identity", candidate, (Verdict.FAIL,) * 5))

    candidate = positive_candidate("M_KP_ND")
    candidate.domain.nd = False
    cases.append(
        (
            "M_KP_ND",
            candidate,
            (Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
        )
    )

    candidate = positive_candidate("M_KG_local")
    candidate.domain.rho = dict(candidate.domain.rho)
    candidate.domain.rho["loop"] = "open"
    cases.append(
        (
            "M_KG_local",
            candidate,
            (Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL, Verdict.FAIL),
        )
    )

    candidate = positive_candidate("M_KCH_collision")
    candidate.domain.ch = replace(candidate.domain.ch, null_collision_probability=0.50)
    cases.append(
        (
            "M_KCH_collision",
            candidate,
            (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL, Verdict.FAIL),
        )
    )

    candidate = positive_candidate("M_KA_projection")
    candidate.across = replace(candidate.across, AB={"b0": "wrong"})
    cases.append(
        (
            "M_KA_projection",
            candidate,
            (Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.PASS, Verdict.FAIL),
        )
    )

    candidate = positive_candidate("M_target_leak")
    candidate.assumption_provenance = AssumptionProvenance(
        entries=("target encoded",), target_encoded=True
    )
    cases.append(("M_target_leak", candidate, (Verdict.FAIL,) * 5))

    candidate = positive_candidate("M_search_leak")
    candidate.search_provenance = SearchProvenance(
        entries=("unlogged search",),
        all_attempts_logged=False,
        stopping_rule_recorded=True,
    )
    cases.append(("M_search_leak", candidate, (Verdict.FAIL,) * 5))

    return cases
