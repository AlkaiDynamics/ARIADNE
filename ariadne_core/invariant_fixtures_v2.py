from __future__ import annotations

from dataclasses import replace

from .invariant_detector_v2 import (
    AcrossSpec,
    CandidateSystem,
    CHSpec,
    CollisionExperiment,
    FiniteMonoid,
    GradedSpec,
    NDPolicy,
    PathSpec,
    Provenance,
)

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"
UNDETERMINED = "UNDETERMINED"


CLEAN_PROVENANCE = {
    "experiment": Provenance(
        assumptions=("synthetic finite fixture",),
        search_steps=("single preregistered fixture construction",),
        target_leakage=False,
        search_path_leakage=False,
        all_attempts_logged=True,
        stopping_rule_recorded=True,
    )
}

STATES = ("e0", "e1", "e2", "e3")
PROJECTION = {"e0": "b0", "e1": "b1", "e2": "b0", "e3": "b1"}
TRANSITION = {"e0": "e2", "e1": "e3", "e2": "e0", "e3": "e1"}
IDENTITY_TRANSITION = {x: x for x in STATES}
VISIBLE_TRANSITION = {"e0": "e1", "e1": "e2", "e2": "e3", "e3": "e0"}

Y = ("y0", "y1", "y2", "y3")
OUT = {"e0": "y0", "e1": "y1", "e2": "y2", "e3": "y3"}
RET = {"y0": "e2", "y1": "e3", "y2": "e0", "y3": "e1"}
TRANSITION_LIFT = (("y0", "y2"), ("y1", "y3"), ("y2", "y0"), ("y3", "y1"))

VALID_PATH = PathSpec(
    exists=True,
    anchor_id="src-anchor",
    intermediate_states=Y,
    outgoing=OUT,
    returning=RET,
    relations={"transition_lift": TRANSITION_LIFT},
    nd_policy=NDPolicy(
        preregistered=True,
        required_relations=("transition_lift",),
    ),
    out_path_id="out",
    return_path_id="return",
)

Z2 = FiniteMonoid(
    elements=("0", "1"),
    identity="0",
    table=(
        ("0", "0", "0"),
        ("0", "1", "1"),
        ("1", "0", "1"),
        ("1", "1", "0"),
    ),
)
Z3 = FiniteMonoid(
    elements=("0", "1", "2"),
    identity="0",
    table=tuple((str(a), str(b), str((a + b) % 3)) for a in range(3) for b in range(3)),
)

GRADED_PATHS = ("id", "out", "return", "gamma", "A", "B", "C", "D")
VALID_RHO = {
    "id": "0",
    "out": "1",
    "return": "1",
    "gamma": "0",
    "A": "0",
    "B": "0",
    "C": "1",
    "D": "1",
}
VALID_H = {
    "id": "0",
    "out": "1",
    "return": "0",
    "gamma": "1",
    "A": "1",
    "B": "2",
    "C": "1",
    "D": "2",
}

VALID_GRADED = GradedSpec(
    exists=True,
    anchor_id="src-anchor",
    paths=GRADED_PATHS,
    identity_path="id",
    gamma="gamma",
    gamma_parts=("out", "return"),
    path_compositions=(("out", "return", "gamma"),),
    rho_labels=VALID_RHO,
    h_labels=VALID_H,
    rho_monoid=Z2,
    h_monoid=Z3,
)

CH_PATHS = ("A", "B", "C", "D")
ALL_NULL_PAIRS = (
    ("A", "B"),
    ("A", "C"),
    ("A", "D"),
    ("B", "C"),
    ("B", "D"),
    ("C", "D"),
)
VALID_CH = CHSpec(
    exists=True,
    anchor_id="src-anchor",
    paths=CH_PATHS,
    internal_classes={"A": "a", "B": "b", "C": "c", "D": "d"},
    realization={"A": "R0", "B": "R0", "C": "R1", "D": "R2"},
    pair=("A", "B"),
    phi_preregistered=True,
    equivalence_preregistered=True,
    collision_experiment=CollisionExperiment(
        preregistered=True,
        equality_rule="EXACT",
        selection_procedure="FIXED_PAIR",
        search_budget=len(ALL_NULL_PAIRS),
        null_pairs=ALL_NULL_PAIRS,
        max_collision_probability=0.20,
    ),
)


def _source(
    name: str,
    *,
    states=STATES,
    projection=PROJECTION,
    transition=TRANSITION,
    witness="e0",
    anchor_id="src-anchor",
    path=VALID_PATH,
    graded=VALID_GRADED,
    ch=VALID_CH,
    across=None,
    provenance=CLEAN_PROVENANCE,
    scope_note=None,
):
    return CandidateSystem(
        name=name,
        states=states,
        projection=projection,
        transition=transition,
        witness=witness,
        anchor_id=anchor_id,
        path=path,
        graded=graded,
        ch=ch,
        across=across,
        provenance=provenance,
        scope_note=scope_note,
    )


T_STATES = ("f0", "f1", "f2", "f3")
T_PROJECTION = {"f0": "c0", "f1": "c1", "f2": "c0", "f3": "c1"}
T_TRANSITION = {"f0": "f2", "f1": "f3", "f2": "f0", "f3": "f1"}
T_Y = ("z0", "z1", "z2", "z3")
T_OUT = {"f0": "z0", "f1": "z1", "f2": "z2", "f3": "z3"}
T_RET = {"z0": "f2", "z1": "f3", "z2": "f0", "z3": "f1"}
T_REL = (("z0", "z2"), ("z1", "z3"), ("z2", "z0"), ("z3", "z1"))
T_PATH = PathSpec(
    exists=True,
    anchor_id="tgt-anchor",
    intermediate_states=T_Y,
    outgoing=T_OUT,
    returning=T_RET,
    relations={"transition_lift": T_REL},
    nd_policy=NDPolicy(preregistered=True, required_relations=("transition_lift",)),
    out_path_id="tout",
    return_path_id="treturn",
)
T_PATHS = ("tid", "tout", "treturn", "tgamma", "TA", "TB", "TC", "TD")
T_GRADED = GradedSpec(
    exists=True,
    anchor_id="tgt-anchor",
    paths=T_PATHS,
    identity_path="tid",
    gamma="tgamma",
    gamma_parts=("tout", "treturn"),
    path_compositions=(("tout", "treturn", "tgamma"),),
    rho_labels={
        "tid": "q0", "tout": "q1", "treturn": "q1", "tgamma": "q0",
        "TA": "q0", "TB": "q0", "TC": "q1", "TD": "q1",
    },
    h_labels={
        "tid": "v0", "tout": "v1", "treturn": "v0", "tgamma": "v1",
        "TA": "v1", "TB": "v2", "TC": "v1", "TD": "v2",
    },
    rho_monoid=FiniteMonoid(
        ("q0", "q1"), "q0",
        (("q0", "q0", "q0"), ("q0", "q1", "q1"), ("q1", "q0", "q1"), ("q1", "q1", "q0")),
    ),
    h_monoid=FiniteMonoid(
        ("v0", "v1", "v2"), "v0",
        tuple((f"v{a}", f"v{b}", f"v{(a+b)%3}") for a in range(3) for b in range(3)),
    ),
)
T_CH = CHSpec(
    exists=True,
    anchor_id="tgt-anchor",
    paths=("TA", "TB", "TC", "TD"),
    internal_classes={"TA": "ta", "TB": "tb", "TC": "tc", "TD": "td"},
    realization={"TA": "S0", "TB": "S0", "TC": "S1", "TD": "S2"},
    pair=("TA", "TB"),
    phi_preregistered=True,
    equivalence_preregistered=True,
    collision_experiment=CollisionExperiment(
        preregistered=True,
        equality_rule="EXACT",
        selection_procedure="FIXED_PAIR",
        search_budget=6,
        null_pairs=(("TA", "TB"), ("TA", "TC"), ("TA", "TD"), ("TB", "TC"), ("TB", "TD"), ("TC", "TD")),
        max_collision_probability=0.20,
    ),
)
TARGET = CandidateSystem(
    name="target_positive",
    states=T_STATES,
    projection=T_PROJECTION,
    transition=T_TRANSITION,
    witness="f0",
    anchor_id="tgt-anchor",
    path=T_PATH,
    graded=T_GRADED,
    ch=T_CH,
    across=None,
    provenance=CLEAN_PROVENANCE,
)

VALID_ACROSS = AcrossSpec(
    exists=True,
    target=TARGET,
    state_map={"e0": "f0", "e1": "f1", "e2": "f2", "e3": "f3"},
    base_map={"b0": "c0", "b1": "c1"},
    intermediate_map={"y0": "z0", "y1": "z1", "y2": "z2", "y3": "z3"},
    path_map={
        "id": "tid", "out": "tout", "return": "treturn", "gamma": "tgamma",
        "A": "TA", "B": "TB", "C": "TC", "D": "TD",
    },
    rho_label_map={"0": "q0", "1": "q1"},
    h_label_map={"0": "v0", "1": "v1", "2": "v2"},
    anchor_map={"src-anchor": "tgt-anchor"},
    adapter_preregistered=True,
    heldout_pass=True,
    low_complexity=True,
)


FIXTURES = {
    "A0": CandidateSystem(
        name="A0_pure_identity",
        states=STATES,
        projection=PROJECTION,
        transition=IDENTITY_TRANSITION,
        witness="e0",
        anchor_id="src-anchor",
        provenance=CLEAN_PROVENANCE,
    ),
    "A1": CandidateSystem(
        name="A1_visible_change",
        states=STATES,
        projection=PROJECTION,
        transition=VISIBLE_TRANSITION,
        witness="e0",
        anchor_id="src-anchor",
        provenance=CLEAN_PROVENANCE,
    ),
    "A2": _source("A2_hidden_displacement_only", path=PathSpec(exists=False, anchor_id="src-anchor"), graded=None, ch=None),
    "A3": _source(
        "A3_trivial_factorization",
        path=PathSpec(
            exists=True,
            anchor_id="src-anchor",
            intermediate_states=tuple(f"tag-{x}" for x in STATES),
            outgoing={x: f"tag-{x}" for x in STATES},
            returning={f"tag-{x}": TRANSITION[x] for x in STATES},
            relations={},
            nd_policy=NDPolicy(preregistered=True, required_relations=("transition_lift",)),
        ),
        graded=None,
        ch=None,
    ),
    "A4": _source(
        "A4_genuine_path_wrong_closure",
        graded=replace(
            VALID_GRADED,
            rho_labels={**VALID_RHO, "return": "0", "gamma": "1"},
        ),
        ch=None,
    ),
    "A5": _source(
        "A5_local_closure_no_global_displacement",
        graded=replace(
            VALID_GRADED,
            h_labels={**VALID_H, "return": "2", "gamma": "0"},
        ),
        ch=None,
    ),
    "A6": _source("A6_genuine_graded_no_ch", ch=CHSpec(exists=False, anchor_id="src-anchor")),
    "A7": _source(
        "A7_fake_ch_coarse_realization",
        ch=replace(
            VALID_CH,
            realization={"A": "R0", "B": "R0", "C": "R0", "D": "R1"},
        ),
    ),
    "A8": _source(
        "A8_fake_ch_target_leakage",
        provenance={
            "experiment": Provenance(
                assumptions=("Phi chosen after target visibility",),
                search_steps=("target inspected before freeze",),
                target_leakage=True,
                search_path_leakage=False,
                all_attempts_logged=True,
                stopping_rule_recorded=True,
            )
        },
        across=None,
    ),
    "A9": _source("A9_genuine_ch_single_domain", across=None),
    "A10": _source(
        "A10_numerical_lookalike_impostor",
        across=replace(VALID_ACROSS, base_map={"b0": "c1", "b1": "c0"}),
    ),
    "A11": _source(
        "A11_partial_across",
        across=replace(VALID_ACROSS, rho_label_map={"0": "q1", "1": "q0"}),
    ),
    "A12": _source(
        "A12_overfit_adapter",
        across=replace(VALID_ACROSS, adapter_preregistered=False),
    ),
    "A13": _source(
        "A13_search_path_p_hack",
        across=VALID_ACROSS,
        provenance={
            "experiment": Provenance(
                assumptions=("broad adapter family",),
                search_steps=("many adapters searched",),
                target_leakage=False,
                search_path_leakage=True,
                all_attempts_logged=False,
                stopping_rule_recorded=True,
            )
        },
    ),
    "A14": _source("A14_genuine_synthetic_across", across=VALID_ACROSS),
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

INTEGRITY_EXPECTED = {
    **{key: PASS for key in FIXTURES},
    "A8": FAIL,
    "A13": FAIL,
}

MUTATIONS = {
    "A0": _source("M_A0_add_hidden_displacement", path=None, graded=None, ch=None),
    "A1": _source("M_A1_hide_transition", path=None, graded=None, ch=None),
    "A2": _source("M_A2_add_valid_path", graded=None, ch=None),
    "A3": _source("M_A3_add_required_relation", graded=None, ch=None),
    "A4": _source("M_A4_fix_local_closure", ch=None),
    "A5": _source("M_A5_restore_global_displacement", ch=None),
    "A6": _source("M_A6_add_valid_ch"),
    "A7": _source("M_A7_restore_low_collision", ch=VALID_CH),
    "A8": _source("M_A8_remove_target_leakage", across=None),
    "A9": _source("M_A9_add_valid_across", across=VALID_ACROSS),
    "A10": _source("M_A10_fix_projection_transport", across=VALID_ACROSS),
    "A11": _source("M_A11_fix_label_transport", across=VALID_ACROSS),
    "A12": _source("M_A12_preregister_adapter", across=VALID_ACROSS),
    "A13": _source("M_A13_log_full_search", across=VALID_ACROSS),
    "A14": _source(
        "M_A14_break_holonomy_transport",
        across=replace(VALID_ACROSS, h_label_map={"0": "v1", "1": "v0", "2": "v2"}),
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

POSITIVE_CONTROLS = {
    "C_KC": _source("C_KC_exact_finite", path=None, graded=None, ch=None, across=None),
    "C_KP": _source("C_KP_exact_finite", graded=None, ch=None, across=None),
    "C_KG": _source("C_KG_exact_finite", ch=None, across=None),
    "C_KCH": _source("C_KCH_exact_finite", across=None),
    "C_KA": FIXTURES["A14"],
}
POSITIVE_EXPECTED = {
    "C_KC": (PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "C_KP": (PASS, PASS, UNDETERMINED, UNDETERMINED, UNDETERMINED),
    "C_KG": (PASS, PASS, PASS, UNDETERMINED, UNDETERMINED),
    "C_KCH": (PASS, PASS, PASS, PASS, UNDETERMINED),
    "C_KA": (PASS, PASS, PASS, PASS, PASS),
}


def r_to_s1_sampled_calibration() -> CandidateSystem:
    states = ("0", "1/4", "1/2", "3/4")
    projection = {
        "0": "0", "1/4": "1/4", "1/2": "1/2", "3/4": "3/4",
        "1": "0", "5/4": "1/4", "3/2": "1/2", "7/4": "3/4",
    }
    transition = {"0": "1", "1/4": "5/4", "1/2": "3/2", "3/4": "7/4"}
    return CandidateSystem(
        name="R_to_S1_sampled_calibration",
        states=states,
        projection=projection,
        transition=transition,
        witness="0",
        anchor_id="cover-sample",
        provenance=CLEAN_PROVENANCE,
        scope_note="SAMPLED_ONLY; universal covering fact requires separate proof",
    )


def collapsing_adapter_candidate() -> CandidateSystem:
    base = FIXTURES["A14"]
    tgt = TARGET
    stationary_target = replace(
        tgt,
        states=tgt.states + ("fs",),
        projection={**tgt.projection, "fs": "cs"},
        transition={**tgt.transition, "fs": "fs"},
        path=replace(
            tgt.path,
            intermediate_states=tgt.path.intermediate_states + ("zs",),
            outgoing={**tgt.path.outgoing, "fs": "zs"},
            returning={**tgt.path.returning, "zs": "fs"},
        ),
    )
    collapsing = replace(
        base.across,
        target=stationary_target,
        state_map={x: "fs" for x in base.states},
        base_map={"b0": "cs", "b1": "cs"},
        intermediate_map={y: "zs" for y in base.path.intermediate_states},
    )
    return replace(base, name="P_KA_designated_movement", across=collapsing)


PREDICATE_MUTATIONS = {
    "Kc_projection_invariant": _source(
        "P_Kc_projection_invariant",
        projection={**PROJECTION, "e2": "bx"},
        witness="e1",
        path=None,
        graded=None,
        ch=None,
        across=None,
    ),
    "Kp_nondegeneracy": replace(
        POSITIVE_CONTROLS["C_KP"],
        name="P_Kp_nondegeneracy",
        path=replace(VALID_PATH, relations={}),
    ),
    "Kg_rho_composition": replace(
        POSITIVE_CONTROLS["C_KG"],
        name="P_Kg_rho_composition",
        graded=replace(
            VALID_GRADED,
            rho_labels={**VALID_RHO, "return": "0", "gamma": "0"},
        ),
    ),
    "KCH_null_collision": replace(
        POSITIVE_CONTROLS["C_KCH"],
        name="P_KCH_null_collision",
        ch=FIXTURES["A7"].ch,
    ),
    "KA_designated_movement": collapsing_adapter_candidate(),
}

PREDICATE_MUTATION_ORACLE = {
    "Kc_projection_invariant": ("Kc", "projection_invariant"),
    "Kp_nondegeneracy": ("Kp", "ND_preregistered_and_nontrivial"),
    "Kg_rho_composition": ("Kg", "rho_respects_composition"),
    "KCH_null_collision": ("KCH", "null_collision_small"),
    "KA_designated_movement": ("KA", "designated_movement_preserved"),
}
