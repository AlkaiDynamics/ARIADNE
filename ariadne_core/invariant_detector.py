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
    """Experiment-integrity metadata attached to one morphology level."""

    assumptions: tuple[str, ...] = ()
    search_steps: tuple[str, ...] = ()
    target_leakage: bool = False
    search_path_leakage: bool = False

    @property
    def valid(self) -> bool:
        return not (self.target_leakage or self.search_path_leakage)


@dataclass(frozen=True)
class PathSpec:
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
class AcrossAdapter:
    """Concrete ACROSS maps used to compute compatibility rather than assert it."""

    target: "CandidateSystem"
    map_E: Optional[Callable[[Any], Any]] = None
    map_B: Optional[Callable[[Any], Any]] = None
    map_Y: Optional[Callable[[Any], Any]] = None
    map_path: Optional[Callable[[Any], Any]] = None
    map_rho: Optional[Callable[[Any], Any]] = None
    map_h: Optional[Callable[[Any], Any]] = None


@dataclass(frozen=True)
class AcrossSpec:
    exists: Optional[bool] = True
    adapter: Optional[AcrossAdapter] = None
    # Legacy/asserted scaffold predicates remain supported for synthetic oracle tests.
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
class IntegrityResult:
    target_leakage_levels: tuple[str, ...] = ()
    search_path_leakage_levels: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not (self.target_leakage_levels or self.search_path_leakage_levels)

    @property
    def verdict(self) -> Verdict:
        return Verdict.PASS if self.valid else Verdict.FAIL

    @property
    def reasons(self) -> tuple[str, ...]:
        reasons = [f"NO_TARGET_LEAKAGE violated at {level}" for level in self.target_leakage_levels]
        reasons.extend(
            f"NO_HIDDEN_SEARCH_PATH_LEAKAGE violated at {level}"
            for level in self.search_path_leakage_levels
        )
        return tuple(reasons)


@dataclass(frozen=True)
class DetectorResult:
    candidate: str
    levels: Mapping[str, LevelResult]
    integrity: IntegrityResult

    @property
    def vector(self) -> tuple[str, str, str, str, str]:
        return tuple(self.levels[level].verdict.value for level in LEVELS)  # type: ignore[return-value]


def _known(value: Any) -> Optional[bool]:
    return True if value is not None else None


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


def _integrity(candidate: CandidateSystem) -> IntegrityResult:
    target = []
    search = []
    for level in LEVELS:
        prov = candidate.provenance.get(level)
        if prov is None:
            continue
        if prov.target_leakage:
            target.append(level)
        if prov.search_path_leakage:
            search.append(level)
    return IntegrityResult(tuple(target), tuple(search))


def _core(candidate: CandidateSystem) -> LevelResult:
    predicates: dict[str, Optional[bool]] = {
        "states_supplied": _known(candidate.states),
        "projection_supplied": _known(candidate.projection),
        "transition_supplied": _known(candidate.transition),
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
    spec = candidate.path
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"path_evidence": None}, ("Kpath not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"admissible_path_exists": False}, ("no admissible nondegenerate traversal",))

    predicates: dict[str, Optional[bool]] = {
        "admissible_path_exists": spec.exists,
        "outgoing_supplied": _known(spec.outgoing),
        "returning_supplied": _known(spec.returning),
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

    if callable(spec.nd):
        predicates["nondegenerate"] = bool(spec.nd())
    elif spec.nd is not None:
        predicates["nondegenerate"] = bool(spec.nd)

    return _aggregate(predicates)


def _graded(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.graded
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"graded_evidence": None}, ("Kgraded not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"graded_path_exists": False}, ("no qualifying graded path",))

    predicates: dict[str, Optional[bool]] = {
        "graded_path_exists": spec.exists,
        "rho_supplied": _known(spec.rho),
        "holonomy_supplied": _known(spec.holonomy),
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


def _safe_all(values: Iterable[bool]) -> bool:
    try:
        return all(values)
    except Exception:
        return False


def _computed_across(candidate: CandidateSystem, adapter: AcrossAdapter) -> Mapping[str, Optional[bool]]:
    target = adapter.target
    computed: dict[str, Optional[bool]] = {
        "target_ch_pass": None,
        "projection_compatible": None,
        "transition_compatible": None,
        "traversal_out_compatible": None,
        "traversal_return_compatible": None,
        "label_compatible": None,
        "holonomy_compatible": None,
        "ch_compatible": None,
    }

    computed["target_ch_pass"] = detect(target).levels["KCH"].verdict is Verdict.PASS

    if (
        candidate.states is not None
        and candidate.projection is not None
        and target.projection is not None
        and adapter.map_E is not None
        and adapter.map_B is not None
    ):
        computed["projection_compatible"] = _safe_all(
            adapter.map_B(candidate.projection(x)) == target.projection(adapter.map_E(x))
            for x in candidate.states
        )

    if (
        candidate.states is not None
        and candidate.transition is not None
        and target.transition is not None
        and adapter.map_E is not None
    ):
        computed["transition_compatible"] = _safe_all(
            adapter.map_E(candidate.transition(x)) == target.transition(adapter.map_E(x))
            for x in candidate.states
        )

    if (
        candidate.states is not None
        and candidate.path is not None
        and target.path is not None
        and candidate.path.outgoing is not None
        and target.path.outgoing is not None
        and adapter.map_E is not None
        and adapter.map_Y is not None
    ):
        computed["traversal_out_compatible"] = _safe_all(
            adapter.map_Y(candidate.path.outgoing(x)) == target.path.outgoing(adapter.map_E(x))
            for x in candidate.states
        )

    if (
        candidate.path is not None
        and target.path is not None
        and candidate.path.intermediate_states is not None
        and candidate.path.returning is not None
        and target.path.returning is not None
        and adapter.map_Y is not None
        and adapter.map_E is not None
    ):
        computed["traversal_return_compatible"] = _safe_all(
            adapter.map_E(candidate.path.returning(y)) == target.path.returning(adapter.map_Y(y))
            for y in candidate.path.intermediate_states
        )

    if (
        candidate.graded is not None
        and target.graded is not None
        and candidate.graded.rho is not None
        and target.graded.rho is not None
        and adapter.map_path is not None
        and adapter.map_rho is not None
    ):
        tokens = (candidate.graded.identity, candidate.graded.gamma)
        computed["label_compatible"] = _safe_all(
            adapter.map_rho(candidate.graded.rho(token))
            == target.graded.rho(adapter.map_path(token))
            for token in tokens
        )

    if (
        candidate.graded is not None
        and target.graded is not None
        and candidate.graded.holonomy is not None
        and target.graded.holonomy is not None
        and adapter.map_path is not None
        and adapter.map_h is not None
    ):
        tokens = (candidate.graded.identity, candidate.graded.gamma)
        computed["holonomy_compatible"] = _safe_all(
            adapter.map_h(candidate.graded.holonomy(token))
            == target.graded.holonomy(adapter.map_path(token))
            for token in tokens
        )

    if (
        candidate.ch is not None
        and target.ch is not None
        and candidate.ch.pair is not None
        and target.ch.internal_equivalent is not None
        and target.ch.realization is not None
        and adapter.map_path is not None
    ):
        a, b = candidate.ch.pair
        ma, mb = adapter.map_path(a), adapter.map_path(b)
        computed["ch_compatible"] = (
            not target.ch.internal_equivalent(ma, mb)
            and target.ch.realization(ma) == target.ch.realization(mb)
        )

    return computed


def _across(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.across
    if spec is None:
        return LevelResult(Verdict.UNDETERMINED, {"across_evidence": None}, ("KACROSS not evaluated",))
    if spec.exists is False:
        return LevelResult(Verdict.FAIL, {"adapter_exists": False}, ("no admissible ACROSS adapter",))

    if spec.adapter is not None:
        compatibility = _computed_across(candidate, spec.adapter)
    else:
        compatibility = {
            "target_ch_pass": spec.target_ch_pass,
            "projection_compatible": spec.projection_compatible,
            "transition_compatible": spec.transition_compatible,
            "traversal_out_compatible": spec.traversal_out_compatible,
            "traversal_return_compatible": spec.traversal_return_compatible,
            "label_compatible": spec.label_compatible,
            "holonomy_compatible": spec.holonomy_compatible,
            "ch_compatible": spec.ch_compatible,
        }

    predicates: dict[str, Optional[bool]] = {
        "adapter_exists": spec.exists,
        **compatibility,
        "adapter_preregistered": spec.adapter_preregistered,
        "heldout_pass": spec.heldout_pass,
        "low_complexity": spec.low_complexity,
    }
    return _aggregate(predicates)


def detect(candidate: CandidateSystem) -> DetectorResult:
    """Evaluate morphology separately from experiment integrity.

    FAIL propagates upward. Lower PARTIAL or UNDETERMINED blocks a higher PASS.
    Provenance leakage never changes D(X); it is reported in result.integrity.
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
    incomplete_below = False

    for level in LEVELS:
        current = raw[level]

        if failed_below:
            current = LevelResult(
                Verdict.FAIL,
                current.predicates,
                current.reasons + ("lower-level FAIL propagated upward",),
            )
        elif incomplete_below and current.verdict is Verdict.PASS:
            current = LevelResult(
                Verdict.PARTIAL,
                current.predicates,
                current.reasons + ("lower-level incompleteness blocks higher PASS",),
            )

        propagated[level] = current
        failed_below = failed_below or current.verdict is Verdict.FAIL
        incomplete_below = incomplete_below or current.verdict in {
            Verdict.PARTIAL,
            Verdict.UNDETERMINED,
        }

    return DetectorResult(
        candidate=candidate.name,
        levels=propagated,
        integrity=_integrity(candidate),
    )
