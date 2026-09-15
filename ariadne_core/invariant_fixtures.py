from __future__ import annotations

import math
from dataclasses import replace
from fractions import Fraction
from typing import Callable

from .invariant_detector import (
    AcrossAdapter,
    AcrossSpec,
    CandidateSystem,
    CHSpec,
    GradedSpec,
    PathSpec,
    Provenance,
)

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
UNDETERMINED = "UNDETERMINED"

STATES = (0, 1, 2, 3)


def parity(x: int) -> int:
    return x % 2


def hidden_tau(x: int) -> int:
    return (x + 2) % 4


def identity_tau(x: int) -> int:
    return x


def visible_tau(x: int) -> int:
    return (x + 1) % 4


Y_STATES = tuple(("Y", x) for x in STATES)


def outgoing(x: int):
    return ("Y", x)


def returning(y):
    return (y[1] + 2) % 4


VALID_PATH = PathSpec(
    exists=True,
    intermediate_states=Y_STATES,
    outgoing=outgoing,
    returning=returning,
    nd=True,
)


def _rho_closed(token):
    return {"id": "same", "gamma": "same"}[token]


def _rho_open(token):
    return {"id": "same", "gamma": "different"}[token]


def _h_displaced(token):
    return {"id": 0, "gamma": 1}[token]


def _h_closed(token):
    return {"id": 0, "gamma": 0}[token]


VALID_GRADED = GradedSpec(
    rho=_rho_closed,
    holonomy=_h_displaced,
    reciprocal_labels=True,
    path_inverse=False,
)


CH_PATHS = ("A", "B", "C", "D")


def _internal_equivalent(a, b):
    return a == b


def _phi_valid(p):
    return {"A": "R0", "B": "R0", "C": "R1", "D": "R2"}[p]


def _phi_coarse(p):
    return {"A": "R0", "B": "R0", "C": "R0", "D": "R1"}[p]


VALID_CH = CHSpec(
    paths=CH_PATHS,
    internal_equivalent=_internal_equivalent,
    realization=_phi_valid,
    pair=("A", "B"),
    phi_preregistered=True,
    equivalence_preregistered=True,
    null_collision_rate=0.01,
    null_threshold=0.05,
)


VALID_ACROSS = AcrossSpec(
    target_ch_pass=True,
    projection_compatible=True,
    transition_compatible=True,
    traversal_out_compatible=True,
    traversal_return_compatible=True,
    label_compatible=True,
    holonomy_compatible=True,
    ch_compatible=True,
    adapter_preregistered=True,
    heldout_pass=True,
    low_complexity=True,
)


def _base(
    name: str,
    *,
    transition: Callable[[int], int] = hidden_tau,
    projection=parity,
    path=VALID_PATH,
    graded=VALID_GRADED,
    ch=VALID_CH,
    across=None,
    provenance=None,
):
    return CandidateSystem(
        name=name,
        states=STATES,
        projection=projection,
        transition=transition,
        witness=0,
        path=path,
        graded=graded,
        ch=ch,
        across=across,
        provenance=provenance or {},
    )


FIXTURES = {
    "A0": CandidateSystem(
        name="A0_pure_identity",
        states=STATES,
        projection=parity,
        transition=identity_tau,
        witness=0,
    ),
    "A1": CandidateSystem(
        name="A1_visible_change",
        states=STATES,
        projection=parity,
        transition=visible_tau,
        witness=0,
    ),
    "A2": _base(
        "A2_hidden_displacement_only",
        path=PathSpec(exists=False),
        graded=None,
        ch=None,
    ),
    "A3": _base(
        "A3_trivial_factorization",
        path=PathSpec(
            exists=True,
            intermediate_states=STATES,
            outgoing=lambda x: x,
            returning=hidden_tau,
            nd=False,
        ),
        graded=None,
        ch=None,
    ),
    "A4": _base(
        "A4_genuine_path_wrong_closure",
        graded=GradedSpec(
            rho=_rho_open,
            holonomy=_h_displaced,
            reciprocal_labels=True,
            path_inverse=False,
        ),
        ch=None,
    ),
    "A5": _base(
        "A5_local_closure_no_global_displacement",
        graded=GradedSpec(
            rho=_rho_closed,
            holonomy=_h_closed,
            reciprocal_labels=True,
            path_inverse=False,
        ),
        ch=None,
    ),
    "A6": _base(
        "A6_genuine_graded_no_ch",
        ch=CHSpec(exists=False),
    ),
    "A7": _base(
        "A7_fake_ch_coarse_realization",
        ch=CHSpec(
            paths=CH_PATHS,
            internal_equivalent=_internal_equivalent,
            realization=_phi_coarse,
            pair=("A", "B"),
            phi_preregistered=True,
            equivalence_preregistered=True,
            null_collision_rate=0.90,
            null_threshold=0.05,
        ),
    ),
    "A8": _base(
        "A8_fake_ch_target_leakage",
        provenance={
            "KCH": Provenance(
                assumptions=("Phi fixed after path inspection",),
                search_steps=("inspected paths before freezing Phi",),
                target_leakage=True,
            )
        },
    ),
    "A9": _base("A9_genuine_ch_single_domain"),
    "A10": _base(
        "A10_numerical_lookalike_impostor",
        across=replace(VALID_ACROSS, projection_compatible=False),
    ),
    "A11": _base(
        "A11_partial_across",
        across=replace(VALID_ACROSS, label_compatible=False),
    ),
    "A12": _base(
        "A12_overfit_adapter",
        across=replace(VALID_ACROSS, adapter_preregistered=False),
    ),
    "A13": _base(
        "A13_search_path_p_hack",
        across=VALID_ACROSS,
        provenance={
            "KA": Provenance(
                assumptions=("adapter family broad",),
                search_steps=("many adapters tried; failures suppressed",),
                search_path_leakage=True,
            )
        },
    ),
    "A14": _base(
        "A14_genuine_synthetic_across",
        across=VALID_ACROSS,
    ),
}


EXPECTED = {
    "A0": (FAIL, FAIL, FAIL, FAIL, FAIL),
    "A1": (FAIL, FAIL, FAIL, FAIL, FAIL),
    "A2": (PASS, FAIL, FAIL, FAIL, FAIL),
    "A3": (PASS, FAIL, FAIL, FAIL, FAIL),
    "A4": (PASS, PASS, FAIL, FAIL, FAIL),
    "A5": (PASS, PASS, FAIL, FAIL, FAIL),
    "A6": (PASS, PASS, PASS, FAIL, FAIL),
    "A7": (PASS, PASS, PASS, FAIL, FAIL),
    "A8": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "A9": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "A10": (PASS, PASS, PASS, PASS, FAIL),
    "A11": (PASS, PASS, PASS, PASS, FAIL),
    "A12": (PASS, PASS, PASS, PASS, FAIL),
    "A13": (PASS, PASS, PASS, PASS, PASS),
    "A14": (PASS, PASS, PASS, PASS, PASS),
}

INTEGRITY_EXPECTED = {key: PASS for key in FIXTURES}
INTEGRITY_EXPECTED["A8"] = FAIL
INTEGRITY_EXPECTED["A13"] = FAIL


MUTATIONS = {
    "A0": _base("M_A0_add_hidden_displacement", path=None, graded=None, ch=None),
    "A1": _base("M_A1_hide_transition", path=None, graded=None, ch=None),
    "A2": _base("M_A2_add_valid_path", graded=None, ch=None),
    "A3": _base(
        "M_A3_make_factorization_nondegenerate",
        path=replace(FIXTURES["A3"].path, nd=True),
        graded=None,
        ch=None,
    ),
    "A4": _base(
        "M_A4_fix_local_closure",
        graded=replace(FIXTURES["A4"].graded, rho=_rho_closed),
        ch=None,
    ),
    "A5": _base("M_A5_restore_global_displacement", ch=None),
    "A6": _base("M_A6_add_valid_ch"),
    "A7": _base(
        "M_A7_make_null_collision_small",
        ch=replace(FIXTURES["A7"].ch, null_collision_rate=0.01),
    ),
    "A8": _base("M_A8_remove_target_leakage"),
    "A9": _base("M_A9_add_valid_across", across=VALID_ACROSS),
    "A10": _base("M_A10_fix_projection_transport", across=VALID_ACROSS),
    "A11": _base("M_A11_fix_label_transport", across=VALID_ACROSS),
    "A12": _base("M_A12_preregister_adapter", across=VALID_ACROSS),
    "A13": _base("M_A13_log_full_search", across=VALID_ACROSS),
    "A14": _base(
        "M_A14_break_holonomy_transport",
        across=replace(VALID_ACROSS, holonomy_compatible=False),
    ),
}


MUTATION_EXPECTED = {
    "A0": (PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "A1": (PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "A2": (PASS, PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "A3": (PASS, PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "A4": (PASS, PASS, PASS, UNDETERMINED, UNDETERMINED),
    "A5": (PASS, PASS, PASS, UNDETERMINED, UNDETERMINED),
    "A6": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "A7": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "A8": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "A9": (PASS, PASS, PASS, PASS, PASS),
    "A10": (PASS, PASS, PASS, PASS, PASS),
    "A11": (PASS, PASS, PASS, PASS, PASS),
    "A12": (PASS, PASS, PASS, PASS, PASS),
    "A13": (PASS, PASS, PASS, PASS, PASS),
    "A14": (PASS, PASS, PASS, PASS, FAIL),
}

MUTATION_INTEGRITY_EXPECTED = {key: PASS for key in MUTATIONS}


def r_to_s1_calibration() -> CandidateSystem:
    """Finite sample-scoped calibration of the standard R -> S1 cover."""

    states = (
        Fraction(0, 1),
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(3, 4),
    )

    def projection(x):
        angle = 2.0 * math.pi * float(x)
        return (round(math.cos(angle), 12), round(math.sin(angle), 12))

    return CandidateSystem(
        name="R_to_S1_cover_calibration_sample_scoped",
        states=states,
        projection=projection,
        transition=lambda x: x + 1,
        witness=Fraction(0, 1),
    )


# --- Level-specific positive controls ---

P_CORE = r_to_s1_calibration()
P_PATH = _base("P_path", graded=None, ch=None, across=None)
P_GRADED = _base("P_graded", ch=None, across=None)
P_CH = _base("P_ch", across=None)

TARGET_STATES = (10, 11, 12, 13)
TARGET_Y_STATES = tuple(("Z", x) for x in TARGET_STATES)


def target_projection(x):
    return "even" if x % 2 == 0 else "odd"


def target_tau(x):
    return 10 + hidden_tau(x - 10)


def target_outgoing(x):
    return ("Z", x)


def target_returning(y):
    return 10 + hidden_tau(y[1] - 10)


def target_rho(token):
    return {"tid": "same", "tgamma": "same"}[token]


def target_h(token):
    return {"tid": 100, "tgamma": 101}[token]


TARGET_CH_PATHS = ("TA", "TB", "TC", "TD")


def target_phi(p):
    return {"TA": "Q0", "TB": "Q0", "TC": "Q1", "TD": "Q2"}[p]


TARGET = CandidateSystem(
    name="P_across_target",
    states=TARGET_STATES,
    projection=target_projection,
    transition=target_tau,
    witness=10,
    path=PathSpec(
        exists=True,
        intermediate_states=TARGET_Y_STATES,
        outgoing=target_outgoing,
        returning=target_returning,
        nd=True,
    ),
    graded=GradedSpec(
        gamma="tgamma",
        identity="tid",
        rho=target_rho,
        holonomy=target_h,
        reciprocal_labels=True,
        path_inverse=False,
    ),
    ch=CHSpec(
        paths=TARGET_CH_PATHS,
        internal_equivalent=_internal_equivalent,
        realization=target_phi,
        pair=("TA", "TB"),
        phi_preregistered=True,
        equivalence_preregistered=True,
        null_collision_rate=0.01,
        null_threshold=0.05,
    ),
)

PATH_MAP = {
    "id": "tid",
    "gamma": "tgamma",
    "A": "TA",
    "B": "TB",
    "C": "TC",
    "D": "TD",
}

VALID_COMPUTED_ADAPTER = AcrossAdapter(
    target=TARGET,
    map_E=lambda x: x + 10,
    map_B=lambda b: "even" if b == 0 else "odd",
    map_Y=lambda y: ("Z", y[1] + 10),
    map_path=lambda p: PATH_MAP[p],
    map_rho=lambda value: value,
    map_h=lambda value: value + 100,
)

P_ACROSS = _base(
    "P_across_computed_maps",
    across=AcrossSpec(
        adapter=VALID_COMPUTED_ADAPTER,
        adapter_preregistered=True,
        heldout_pass=True,
        low_complexity=True,
    ),
)

POSITIVE_CONTROLS = {
    "Pc": P_CORE,
    "Pp": P_PATH,
    "Pg": P_GRADED,
    "Pch": P_CH,
    "Pa": P_ACROSS,
}

POSITIVE_EXPECTED = {
    "Pc": (PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "Pp": (PASS, PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "Pg": (PASS, PASS, PASS, UNDETERMINED, UNDETERMINED),
    "Pch": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "Pa": (PASS, PASS, PASS, PASS, PASS),
}


# Predicate-isolating mutations from otherwise valid candidates.
def partly_visible_projection(x):
    return {0: 0, 2: 0, 1: 1, 3: 2}[x]


PREDICATE_MUTATIONS = {
    "Kc_projection_invariant": _base(
        "M_predicate_Kc_projection_invariant",
        projection=partly_visible_projection,
        across=VALID_ACROSS,
    ),
    "Kp_nondegenerate": _base(
        "M_predicate_Kp_nondegenerate",
        path=replace(VALID_PATH, nd=False),
        across=VALID_ACROSS,
    ),
    "Kg_local_closure": _base(
        "M_predicate_Kg_local_closure",
        graded=replace(VALID_GRADED, rho=_rho_open),
        across=VALID_ACROSS,
    ),
    "KCH_null_collision": _base(
        "M_predicate_KCH_null_collision",
        ch=replace(VALID_CH, null_collision_rate=0.90),
        across=VALID_ACROSS,
    ),
    "KA_label_compatibility": replace(
        P_ACROSS,
        name="M_predicate_KA_label_compatibility",
        across=replace(
            P_ACROSS.across,
            adapter=replace(VALID_COMPUTED_ADAPTER, map_rho=lambda value: f"bad:{value}"),
        ),
    ),
}

PREDICATE_MUTATION_EXPECTED = {
    "Kc_projection_invariant": (FAIL, FAIL, FAIL, FAIL, FAIL),
    "Kp_nondegenerate": (PASS, FAIL, FAIL, FAIL, FAIL),
    "Kg_local_closure": (PASS, PASS, FAIL, FAIL, FAIL),
    "KCH_null_collision": (PASS, PASS, PASS, FAIL, FAIL),
    "KA_label_compatibility": (PASS, PASS, PASS, PASS, FAIL),
}
