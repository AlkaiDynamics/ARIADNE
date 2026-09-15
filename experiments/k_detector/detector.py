from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Tuple


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNDETERMINED = "UNDETERMINED"


LEVELS = ("Kc", "Kp", "Kg", "KCH", "KA")


@dataclass(frozen=True)
class CHSpec:
    gamma_a: str
    gamma_b: str
    internally_equivalent: Optional[bool]
    phi: Optional[Mapping[str, Any]]
    phi_fixed_before_observation: Optional[bool]
    null_collision_probability: Optional[float]
    max_collision_probability: Optional[float]


@dataclass
class MorphologyDomain:
    name: str
    E: Optional[Tuple[Any, ...]]
    B: Optional[Tuple[Any, ...]]
    pi: Optional[Mapping[Any, Any]]
    tau: Optional[Mapping[Any, Any]]
    Y: Optional[Tuple[Any, ...]] = None
    out: Optional[Mapping[Any, Any]] = None
    ret: Optional[Mapping[Any, Any]] = None
    nd: Optional[bool] = None
    paths: Optional[Tuple[str, ...]] = None
    rho: Optional[Mapping[str, Any]] = None
    h: Optional[Mapping[str, Any]] = None
    gamma: Optional[str] = None
    identity_path: Optional[str] = None
    ch: Optional[CHSpec] = None


@dataclass(frozen=True)
class AcrossSpec:
    target: MorphologyDomain
    AE: Optional[Mapping[Any, Any]]
    AB: Optional[Mapping[Any, Any]]
    AY: Optional[Mapping[Any, Any]]
    AGamma: Optional[Mapping[str, str]]
    ASrho: Optional[Mapping[Any, Any]] = None
    ASh: Optional[Mapping[Any, Any]] = None


@dataclass(frozen=True)
class AssumptionProvenance:
    entries: Tuple[str, ...] = ()
    target_encoded: bool = False


@dataclass(frozen=True)
class SearchProvenance:
    entries: Tuple[str, ...] = ()
    all_attempts_logged: bool = True
    stopping_rule_recorded: bool = True


@dataclass
class CandidateSystem:
    name: str
    domain: MorphologyDomain
    across: Optional[AcrossSpec] = None
    assumption_provenance: AssumptionProvenance = field(default_factory=AssumptionProvenance)
    search_provenance: SearchProvenance = field(default_factory=SearchProvenance)


@dataclass(frozen=True)
class LevelResult:
    verdict: Verdict
    checks: Tuple[Tuple[str, Optional[bool]], ...]
    reason: str = ""


@dataclass(frozen=True)
class DetectionResult:
    candidate: str
    results: Mapping[str, LevelResult]
    integrity_failures: Tuple[str, ...] = ()

    @property
    def vector(self):
        return tuple(self.results[level].verdict for level in LEVELS)

    def as_dict(self):
        return {level: self.results[level].verdict.value for level in LEVELS}


def _total(mapping, domain):
    if mapping is None or domain is None:
        return None
    return all(x in mapping for x in domain)


def _classify(checks):
    values = [value for _, value in checks]
    if any(value is False for value in values):
        failed = ", ".join(name for name, value in checks if value is False)
        return LevelResult(Verdict.FAIL, tuple(checks), "failed: " + failed)
    known = [value for value in values if value is not None]
    if not known:
        return LevelResult(Verdict.UNDETERMINED, tuple(checks), "no required evidence evaluated")
    if any(value is None for value in values):
        return LevelResult(Verdict.PARTIAL, tuple(checks), "some required evidence is unresolved")
    return LevelResult(Verdict.PASS, tuple(checks), "all required predicates satisfied")


def _core(domain):
    total_tau = _total(domain.tau, domain.E)
    total_pi = _total(domain.pi, domain.E)
    moved = preserved = witness = None

    if total_tau and total_pi:
        moved_states = [x for x in domain.E if domain.tau[x] != x]
        moved = bool(moved_states)
        images_valid = all(domain.tau[x] in domain.pi for x in domain.E)
        preserved = (
            all(domain.pi[domain.tau[x]] == domain.pi[x] for x in domain.E)
            if images_valid
            else False
        )
        witness = (
            any(
                domain.tau[x] != x
                and domain.pi[domain.tau[x]] == domain.pi[x]
                for x in domain.E
            )
            if images_valid
            else False
        )

    return _classify(
        (
            ("tau_total_on_E", total_tau),
            ("pi_total_on_E", total_pi),
            ("W_tau_nonempty", moved),
            ("pi_after_tau_equals_pi", preserved),
            ("hidden_displacement_witness_exists", witness),
        )
    )


def _path(domain):
    out_total = _total(domain.out, domain.E)
    ret_total = _total(domain.ret, domain.Y)
    composition = typed = None

    if (
        out_total
        and ret_total
        and domain.tau is not None
        and domain.E is not None
        and domain.Y is not None
    ):
        typed = all(domain.out[x] in domain.Y for x in domain.E) and all(
            domain.ret[y] in domain.E for y in domain.Y
        )
        composition = (
            all(domain.ret[domain.out[x]] == domain.tau[x] for x in domain.E)
            if typed
            else False
        )

    y_present = (
        domain.Y is not None
        if domain.Y is not None or domain.out is not None or domain.ret is not None
        else None
    )

    return _classify(
        (
            ("Y_present", y_present),
            ("out_total", out_total),
            ("ret_total", ret_total),
            ("typed_traversal", typed),
            ("return_after_out_equals_tau", composition),
            ("ND", domain.nd),
        )
    )


def _graded(domain):
    paths_present = domain.paths is not None
    gamma_present = id_present = rho_total = h_total = None
    local_closure = global_nonclosure = None

    if paths_present:
        gamma_present = domain.gamma in domain.paths if domain.gamma is not None else None
        id_present = (
            domain.identity_path in domain.paths
            if domain.identity_path is not None
            else None
        )
        if domain.gamma is not None and domain.identity_path is not None:
            rho_total = _total(domain.rho, (domain.gamma, domain.identity_path))
            h_total = _total(domain.h, (domain.gamma, domain.identity_path))
        if gamma_present and id_present and rho_total:
            local_closure = domain.rho[domain.gamma] == domain.rho[domain.identity_path]
        if gamma_present and id_present and h_total:
            global_nonclosure = domain.h[domain.gamma] != domain.h[domain.identity_path]

    return _classify(
        (
            ("Gamma_present", paths_present),
            ("gamma_present", gamma_present),
            ("identity_path_present", id_present),
            ("rho_defined", rho_total),
            ("h_defined", h_total),
            ("local_relational_closure", local_closure),
            ("global_displacement_nontrivial", global_nonclosure),
        )
    )


def _ch(domain):
    spec = domain.ch
    if spec is None:
        return _classify((("CH_spec_present", None),))

    pair_present = phi_pair_defined = realization_collision = None
    discriminative = collision_small = None

    if domain.paths is not None:
        pair_present = spec.gamma_a in domain.paths and spec.gamma_b in domain.paths

    if spec.phi is not None:
        phi_pair_defined = spec.gamma_a in spec.phi and spec.gamma_b in spec.phi
        if phi_pair_defined:
            realization_collision = spec.phi[spec.gamma_a] == spec.phi[spec.gamma_b]
        values = list(spec.phi.values())
        discriminative = len(set(values)) >= 2 if values else False

    if (
        spec.null_collision_probability is not None
        and spec.max_collision_probability is not None
    ):
        collision_small = (
            spec.null_collision_probability <= spec.max_collision_probability
        )

    inequivalent = (
        None
        if spec.internally_equivalent is None
        else not spec.internally_equivalent
    )

    return _classify(
        (
            ("CH_pair_present", pair_present),
            ("internally_inequivalent", inequivalent),
            ("Phi_pair_defined", phi_pair_defined),
            ("same_realization", realization_collision),
            ("Phi_fixed_before_pair", spec.phi_fixed_before_observation),
            ("Phi_discriminative", discriminative),
            ("null_collision_small", collision_small),
        )
    )


def _across(source, across):
    if across is None:
        return _classify((("ACROSS_spec_present", None),))

    target = across.target
    ae_total = _total(across.AE, source.E)
    ab_total = _total(across.AB, source.B)
    ay_total = _total(across.AY, source.Y)
    ag_total = _total(across.AGamma, source.paths)

    projection = transition = out_commute = ret_commute = None
    rho_commute = h_commute = ch_compat = None

    if ae_total and ab_total and source.E is not None and source.pi is not None and target.pi is not None:
        projection = all(
            source.pi[x] in across.AB
            and across.AE[x] in target.pi
            and across.AB[source.pi[x]] == target.pi[across.AE[x]]
            for x in source.E
        )

    if ae_total and source.E is not None and source.tau is not None and target.tau is not None:
        transition = all(
            source.tau[x] in across.AE
            and across.AE[x] in target.tau
            and across.AE[source.tau[x]] == target.tau[across.AE[x]]
            for x in source.E
        )

    if ae_total and ay_total and source.E is not None and source.out is not None and target.out is not None:
        out_commute = all(
            source.out[x] in across.AY
            and across.AE[x] in target.out
            and across.AY[source.out[x]] == target.out[across.AE[x]]
            for x in source.E
        )

    if ae_total and ay_total and source.Y is not None and source.ret is not None and target.ret is not None:
        ret_commute = all(
            source.ret[y] in across.AE
            and across.AY[y] in target.ret
            and across.AE[source.ret[y]] == target.ret[across.AY[y]]
            for y in source.Y
        )

    if (
        ag_total
        and across.ASrho is not None
        and source.paths is not None
        and source.rho is not None
        and target.rho is not None
    ):
        rho_commute = all(
            path in source.rho
            and source.rho[path] in across.ASrho
            and across.AGamma[path] in target.rho
            and across.ASrho[source.rho[path]] == target.rho[across.AGamma[path]]
            for path in source.paths
        )

    if (
        ag_total
        and across.ASh is not None
        and source.paths is not None
        and source.h is not None
        and target.h is not None
    ):
        h_commute = all(
            path in source.h
            and source.h[path] in across.ASh
            and across.AGamma[path] in target.h
            and across.ASh[source.h[path]] == target.h[across.AGamma[path]]
            for path in source.paths
        )

    if source.ch is not None and target.ch is not None and ag_total:
        mapped_pair = {
            across.AGamma[source.ch.gamma_a],
            across.AGamma[source.ch.gamma_b],
        }
        target_pair = {target.ch.gamma_a, target.ch.gamma_b}
        ch_compat = mapped_pair == target_pair

    return _classify(
        (
            ("AE_total", ae_total),
            ("AB_total", ab_total),
            ("AY_total", ay_total),
            ("AGamma_total", ag_total),
            ("projection_commutes", projection),
            ("transition_commutes", transition),
            ("out_commutes", out_commute),
            ("return_commutes", ret_commute),
            ("rho_commutes", rho_commute),
            ("h_commutes", h_commute),
            ("CH_compatible", ch_compat),
        )
    )


def _apply_prerequisite(raw, previous):
    if previous.verdict == Verdict.FAIL:
        return LevelResult(
            Verdict.FAIL,
            raw.checks,
            "forced FAIL by failed lower-level prerequisite",
        )
    if previous.verdict == Verdict.UNDETERMINED and raw.verdict == Verdict.PASS:
        return LevelResult(
            Verdict.PARTIAL,
            raw.checks,
            "cannot PASS above an UNDETERMINED prerequisite",
        )
    return raw


def detect(candidate):
    integrity = []
    if candidate.assumption_provenance.target_encoded:
        integrity.append("TARGET_LEAKAGE")
    if not candidate.search_provenance.all_attempts_logged:
        integrity.append("SEARCH_PATH_LEAKAGE")
    if not candidate.search_provenance.stopping_rule_recorded:
        integrity.append("SEARCH_STOPPING_RULE_MISSING")

    if integrity:
        failed = {
            level: LevelResult(
                Verdict.FAIL,
                (("constitutional_integrity", False),),
                "constitutional rejection: " + ", ".join(integrity),
            )
            for level in LEVELS
        }
        return DetectionResult(candidate.name, failed, tuple(integrity))

    kc = _core(candidate.domain)
    kp = _apply_prerequisite(_path(candidate.domain), kc)
    kg = _apply_prerequisite(_graded(candidate.domain), kp)
    kch = _apply_prerequisite(_ch(candidate.domain), kg)
    ka = _apply_prerequisite(_across(candidate.domain, candidate.across), kch)

    return DetectionResult(
        candidate.name,
        {"Kc": kc, "Kp": kp, "Kg": kg, "KCH": kch, "KA": ka},
    )
