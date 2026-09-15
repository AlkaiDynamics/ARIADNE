from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNDETERMINED = "UNDETERMINED"


LEVELS = ("Kc", "Kp", "Kg", "KCH", "KA")


@dataclass(frozen=True)
class Provenance:
    """Constitutional provenance gate for one detector level."""

    assumptions: tuple[str, ...] = ()
    search_steps: tuple[str, ...] = ()
    target_leakage: bool = False
    search_path_leakage: bool = False

    @property
    def valid(self) -> bool:
        return not (self.target_leakage or self.search_path_leakage)


@dataclass(frozen=True)
class PathSpec:
    """Evidence for Kpath.

    exists=False means a bounded/pre-registered search established that no
    admissible factorization exists. exists=None means it has not been resolved.
    """

    exists: Optional[bool] = True
    intermediate_states: Optional[Sequence[Any]] = None
    outgoing: Optional[Callable[[Any], Any]] = None
    returning: Optional[Callable[[Any], Any]] = None
    nd: Optional[Callable[[], bool] | bool] = None


@dataclass(frozen=True)
class GradedSpec:
    exists: Optional[bool] = True
    gamma: Any = "gamma"
    identity: Any = "id"
    rho: Optional[Callable[[Any], Any]] = None
    holonomy: Optional[Callable[[Any], Any]] = None
    reciprocal_labels: Optional[bool] = None
    path_inverse: Optional[bool] = False


@dataclass(frozen=True)
class CHSpec:
    exists: Optional[bool] = True
    paths: Optional[Sequence[Any]] = None
    internal_equivalent: Optional[Callable[[Any, Any], bool]] = None
    realization: Optional[Callable[[Any], Any]] = None
    pair: Optional[tuple[Any, Any]] = None
    phi_preregistered: Optional[bool] = None
    equivalence_preregistered: Optional[bool] = None
    null_collision_rate: Optional[float] = None
    null_threshold: Optional[float] = None


@dataclass(frozen=True)
class AcrossSpec:
    exists: Optional[bool] = True
    target_ch_pass: Optional[bool] = None
    projection_compatible: Optional[bool] = None
    transition_compatible: Optional[bool] = None
    traversal_out_compatible: Optional[bool] = None
    traversal_return_compatible: Optional[bool] = None
    label_compatible: Optional[bool] = None
    holonomy_compatible: Optional[bool] = None
    ch_compatible: Optional[bool] = None
    adapter_preregistered: Optional[bool] = None
    heldout_pass: Optional[bool] = None
    low_complexity: Optional[bool] = None


@dataclass(frozen=True)
class CandidateSystem:
    name: str
    states: Optional[Sequence[Any]] = None
    projection: Optional[Callable[[Any], Any]] = None
    transition: Optional[Callable[[Any], Any]] = None
    witness: Any = None
    path: Optional[PathSpec] = None
    graded: Optional[GradedSpec] = None
    ch: Optional[CHSpec] = None
    across: Optional[AcrossSpec] = None
    provenance: Mapping[str, Provenance] = field(default_factory=dict)


@dataclass(frozen=True)
class LevelResult:
    verdict: Verdict
    predicates: Mapping[str, Optional[bool]]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetectorResult:
    candidate: str
    levels: Mapping[str, LevelResult]

    @property
    def vector(self) -> tuple[str, str, str, str, str]:
        return tuple(self.levels[level].verdict.value for level in LEVELS)  # type: ignore[return-value]


def _aggregate(predicates: Mapping[str, Optional[bool]], reasons: Iterable[str] = ()) -> LevelResult:
    vals = tuple(predicates.values())
    if any(value is False for value in vals):
        verdict = Verdict.FAIL
    elif vals and all(value is True for value in vals):
        verdict = Verdict.PASS
    elif any(value is True for value in vals):
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.UNDETERMINED
    return LevelResult(verdict=verdict, predicates=dict(predicates), reasons=tuple(reasons))


def _provenance_gate(candidate: CandidateSystem, level: str) -> Optional[LevelResult]:
    prov = candidate.provenance.get(level)
    if prov is None or prov.valid:
        return None
    reasons = []
    if prov.target_leakage:
        reasons.append("NO_TARGET_LEAKAGE violated")
    if prov.search_path_leakage:
        reasons.append("NO_HIDDEN_SEARCH_PATH_LEAKAGE violated")
    return LevelResult(
        verdict=Verdict.FAIL,
        predicates={"provenance": False},
        reasons=tuple(reasons),
    )


def _core(candidate: CandidateSystem) -> LevelResult:
    prov = _provenance_gate(candidate, "Kc")
    if prov:
        return prov

    predicates: dict[str, Optional[bool]] = {
        "states_supplied": candidate.states is not None,
        "projection_supplied": candidate.projection is not None,
        "transition_supplied": candidate.transition is not None,
        "moved_state_exists": None,
        "projection_invariant": None,
        "witness_valid": None,
    }

    if candidate.states is None or candidate.projection is None or candidate.transition is None:
        return _aggregate(predicates, ("core data incomplete",))

    states = tuple(candidate.states)
    if not states:
        predicates["moved_state_exists"] = False
        predicates["projection_invariant"] = True
        predicates["witness_valid"] = False
        return _aggregate(predicates, ("E has no moved witness",))

    moved = [x for x in states if candidate.transition(x) != x]
    predicates["moved_state_exists"] = bool(moved)
    predicates["projection_invariant"] = all(
        candidate.projection(candidate.transition(x)) == candidate.projection(x)
        for x in states
    )

    witness = candidate.witness
    if witness is None:
        witness = moved[0] if moved else None
    predicates["witness_valid"] = bool(
        witness is not None
        and witness in states
        and candidate.transition(witness) != witness
        and candidate.projection(candidate.transition(witness)) == candidate.projection(witness)
    )
    return _aggregate(predicates)


def _path(candidate: CandidateSystem) -> LevelResult:
    prov = _provenance_gate(candidate, "Kp")
    if prov:
        return prov
    spec = candidate.path
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"path_evidence": None}, ("Kpath not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"admissible_path_exists": False}, ("no admissible nondegenerate traversal",))

    predicates: dict[str, Optional[bool]] = {
        "admissible_path_exists": spec.exists,
        "outgoing_supplied": spec.outgoing is not None,
        "returning_supplied": spec.returning is not None,
        "composition_equals_tau": None,
        "typed_intermediate": None,
        "nondegenerate": None,
    }

    if candidate.states is not None and candidate.transition is not None and spec.outgoing and spec.returning:
        predicates["composition_equals_tau"] = all(
            spec.returning(spec.outgoing(x)) == candidate.transition(x)
            for x in candidate.states
        )
        if spec.intermediate_states is not None:
            allowed = tuple(spec.intermediate_states)
            predicates["typed_intermediate"] = all(spec.outgoing(x) in allowed for x in candidate.states)
        else:
            predicates["typed_intermediate"] = None

    if callable(spec.nd):
        predicates["nondegenerate"] = bool(spec.nd())
    elif spec.nd is None:
        predicates["nondegenerate"] = None
    else:
        predicates["nondegenerate"] = bool(spec.nd)

    return _aggregate(predicates)


def _graded(candidate: CandidateSystem) -> LevelResult:
    prov = _provenance_gate(candidate, "Kg")
    if prov:
        return prov
    spec = candidate.graded
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"graded_evidence": None}, ("Kgraded not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"graded_path_exists": False}, ("no qualifying graded path",))

    predicates: dict[str, Optional[bool]] = {
        "graded_path_exists": spec.exists,
        "rho_supplied": spec.rho is not None,
        "holonomy_supplied": spec.holonomy is not None,
        "local_closure": None,
        "global_nonclosure": None,
        "label_reciprocity": spec.reciprocal_labels,
        "not_path_inverse": None if spec.path_inverse is None else (not spec.path_inverse),
    }
    if spec.rho:
        predicates["local_closure"] = spec.rho(spec.gamma) == spec.rho(spec.identity)
    if spec.holonomy:
        predicates["global_nonclosure"] = spec.holonomy(spec.gamma) != spec.holonomy(spec.identity)
    return _aggregate(predicates)


def _ch(candidate: CandidateSystem) -> LevelResult:
    prov = _provenance_gate(candidate, "KCH")
    if prov:
        return prov
    spec = candidate.ch
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"ch_evidence": None}, ("KCH not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"qualifying_pair_exists": False}, ("no qualifying CH pair",))

    predicates: dict[str, Optional[bool]] = {
        "qualifying_pair_exists": spec.exists,
        "phi_preregistered": spec.phi_preregistered,
        "equivalence_preregistered": spec.equivalence_preregistered,
        "internally_inequivalent": None,
        "same_realization": None,
        "phi_discriminative": None,
        "null_collision_small": None,
    }

    if spec.pair and spec.internal_equivalent:
        a, b = spec.pair
        predicates["internally_inequivalent"] = not spec.internal_equivalent(a, b)
    if spec.pair and spec.realization:
        a, b = spec.pair
        predicates["same_realization"] = spec.realization(a) == spec.realization(b)

    if spec.paths is not None and spec.realization is not None:
        realized = [spec.realization(p) for p in spec.paths]
        predicates["phi_discriminative"] = len(set(realized)) > 1

    if spec.null_collision_rate is not None and spec.null_threshold is not None:
        predicates["null_collision_small"] = spec.null_collision_rate <= spec.null_threshold

    return _aggregate(predicates)


def _across(candidate: CandidateSystem) -> LevelResult:
    prov = _provenance_gate(candidate, "KA")
    if prov:
        return prov
    spec = candidate.across
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"across_evidence": None}, ("KACROSS not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"adapter_exists": False}, ("no admissible ACROSS adapter",))

    predicates: dict[str, Optional[bool]] = {
        "adapter_exists": spec.exists,
        "target_ch_pass": spec.target_ch_pass,
        "projection_compatible": spec.projection_compatible,
        "transition_compatible": spec.transition_compatible,
        "traversal_out_compatible": spec.traversal_out_compatible,
        "traversal_return_compatible": spec.traversal_return_compatible,
        "label_compatible": spec.label_compatible,
        "holonomy_compatible": spec.holonomy_compatible,
        "ch_compatible": spec.ch_compatible,
        "adapter_preregistered": spec.adapter_preregistered,
        "heldout_pass": spec.heldout_pass,
        "low_complexity": spec.low_complexity,
    }
    return _aggregate(predicates)


def detect(candidate: CandidateSystem) -> DetectorResult:
    """Evaluate the frozen five-level morphology.

    FAIL propagates upward. UNDETERMINED cannot support a higher PASS.
    PARTIAL is retained as evidence-bearing incompleteness and does not, by
    itself, force a higher-level demotion.
    """

    evaluators = {
        "Kc": _core,
        "Kp": _path,
        "Kg": _graded,
        "KCH": _ch,
        "KA": _across,
    }
    raw = {level: evaluators[level](candidate) for level in LEVELS}

    propagated: dict[str, LevelResult] = {}
    failed_below = False
    undetermined_below = False

    for level in LEVELS:
        current = raw[level]

        if failed_below:
            current = LevelResult(
                Verdict.FAIL,
                current.predicates,
                current.reasons + ("lower-level FAIL propagated upward",),
            )
        elif undetermined_below and current.verdict is Verdict.PASS:
            current = LevelResult(
                Verdict.PARTIAL,
                current.predicates,
                current.reasons + ("lower-level UNDETERMINED blocks higher PASS",),
            )

        propagated[level] = current
        failed_below = failed_below or current.verdict is Verdict.FAIL
        undetermined_below = undetermined_below or current.verdict is Verdict.UNDETERMINED

    return DetectorResult(candidate=candidate.name, levels=propagated)
