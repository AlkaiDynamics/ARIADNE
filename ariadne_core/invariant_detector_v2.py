from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping, Optional, Sequence


DETECTOR_SPEC_VERSION = "2.0.0"
ND_POLICY_V1 = "ND_V1_REQUIRED_TRANSITION_RELATION"
LEVELS = ("Kc", "Kp", "Kg", "KCH", "KA")


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class Provenance:
    assumptions: tuple[str, ...] = ()
    search_steps: tuple[str, ...] = ()
    target_leakage: Optional[bool] = None
    search_path_leakage: Optional[bool] = None
    all_attempts_logged: Optional[bool] = None
    stopping_rule_recorded: Optional[bool] = None


@dataclass(frozen=True)
class NDPolicy:
    policy_id: str = ND_POLICY_V1
    preregistered: Optional[bool] = None
    required_relations: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathSpec:
    exists: Optional[bool] = True
    anchor_id: Optional[str] = None
    intermediate_states: Optional[tuple[str, ...]] = None
    outgoing: Optional[Mapping[str, str]] = None
    returning: Optional[Mapping[str, str]] = None
    relations: Mapping[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)
    nd_policy: Optional[NDPolicy] = None
    out_path_id: Optional[str] = "out"
    return_path_id: Optional[str] = "return"


@dataclass(frozen=True)
class FiniteMonoid:
    elements: tuple[str, ...]
    identity: str
    table: tuple[tuple[str, str, str], ...]

    def _lookup(self) -> dict[tuple[str, str], str]:
        return {(a, b): c for a, b, c in self.table}

    def combine(self, a: str, b: str) -> Optional[str]:
        return self._lookup().get((a, b))

    def validate(self) -> bool:
        elems = set(self.elements)
        if self.identity not in elems:
            return False
        lookup = self._lookup()
        if len(lookup) != len(self.table):
            return False
        for a in self.elements:
            for b in self.elements:
                c = lookup.get((a, b))
                if c is None or c not in elems:
                    return False
        for a in self.elements:
            if lookup[(self.identity, a)] != a or lookup[(a, self.identity)] != a:
                return False
        for a in self.elements:
            for b in self.elements:
                for c in self.elements:
                    left = lookup[(lookup[(a, b)], c)]
                    right = lookup[(a, lookup[(b, c)])]
                    if left != right:
                        return False
        return True


@dataclass(frozen=True)
class GradedSpec:
    exists: Optional[bool] = True
    anchor_id: Optional[str] = None
    paths: Optional[tuple[str, ...]] = None
    identity_path: Optional[str] = None
    gamma: Optional[str] = None
    gamma_parts: Optional[tuple[str, str]] = None
    path_compositions: tuple[tuple[str, str, str], ...] = ()
    rho_labels: Optional[Mapping[str, str]] = None
    h_labels: Optional[Mapping[str, str]] = None
    rho_monoid: Optional[FiniteMonoid] = None
    h_monoid: Optional[FiniteMonoid] = None


@dataclass(frozen=True)
class CollisionExperiment:
    preregistered: Optional[bool] = None
    equality_rule: Optional[str] = None
    selection_procedure: Optional[str] = None
    search_budget: Optional[int] = None
    null_pairs: Optional[tuple[tuple[str, str], ...]] = None
    max_collision_probability: Optional[float] = None


@dataclass(frozen=True)
class CHSpec:
    exists: Optional[bool] = True
    anchor_id: Optional[str] = None
    paths: Optional[tuple[str, ...]] = None
    internal_classes: Optional[Mapping[str, str]] = None
    realization: Optional[Mapping[str, str]] = None
    pair: Optional[tuple[str, str]] = None
    phi_preregistered: Optional[bool] = None
    equivalence_preregistered: Optional[bool] = None
    collision_experiment: Optional[CollisionExperiment] = None


@dataclass(frozen=True)
class AcrossSpec:
    exists: Optional[bool] = True
    target: Optional["CandidateSystem"] = None
    state_map: Optional[Mapping[str, str]] = None
    base_map: Optional[Mapping[str, str]] = None
    intermediate_map: Optional[Mapping[str, str]] = None
    path_map: Optional[Mapping[str, str]] = None
    rho_label_map: Optional[Mapping[str, str]] = None
    h_label_map: Optional[Mapping[str, str]] = None
    anchor_map: Optional[Mapping[str, str]] = None
    adapter_preregistered: Optional[bool] = None
    heldout_pass: Optional[bool] = None
    low_complexity: Optional[bool] = None


@dataclass(frozen=True)
class CandidateSystem:
    name: str
    states: Optional[tuple[str, ...]] = None
    projection: Optional[Mapping[str, str]] = None
    transition: Optional[Mapping[str, str]] = None
    witness: Optional[str] = None
    anchor_id: Optional[str] = None
    path: Optional[PathSpec] = None
    graded: Optional[GradedSpec] = None
    ch: Optional[CHSpec] = None
    across: Optional[AcrossSpec] = None
    provenance: Mapping[str, Provenance] = field(default_factory=dict)
    scope_note: Optional[str] = None


@dataclass(frozen=True)
class LevelResult:
    independent_verdict: Verdict
    verdict: Verdict
    predicates: Mapping[str, Optional[bool]]
    reasons: tuple[str, ...] = ()
    prerequisite_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntegrityReport:
    target_leakage: Verdict
    search_path_leakage: Verdict
    search_ledger_complete: Verdict
    stopping_rule_recorded: Verdict
    overall: Verdict
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetectorResult:
    candidate: str
    spec_version: str
    levels: Mapping[str, LevelResult]
    integrity: IntegrityReport

    @property
    def vector(self) -> tuple[str, str, str, str, str]:
        return tuple(self.levels[level].verdict.value for level in LEVELS)  # type: ignore[return-value]

    @property
    def independent_vector(self) -> tuple[str, str, str, str, str]:
        return tuple(self.levels[level].independent_verdict.value for level in LEVELS)  # type: ignore[return-value]


def _aggregate(predicates: Mapping[str, Optional[bool]]) -> Verdict:
    values = tuple(predicates.values())
    if any(value is False for value in values):
        return Verdict.FAIL
    known_true = any(value is True for value in values)
    unresolved = any(value is None for value in values)
    if known_true and unresolved:
        return Verdict.PARTIAL
    if values and all(value is True for value in values):
        return Verdict.PASS
    return Verdict.UNDETERMINED


def _level(predicates: Mapping[str, Optional[bool]], *reasons: str) -> LevelResult:
    independent = _aggregate(predicates)
    return LevelResult(independent, independent, dict(predicates), tuple(r for r in reasons if r))


def _integrity(candidate: CandidateSystem) -> IntegrityReport:
    records = tuple(candidate.provenance.values())
    if not records:
        u = Verdict.UNDETERMINED
        return IntegrityReport(u, u, u, u, u, ("no experiment-integrity record supplied",))

    def leakage_status(attr: str) -> Verdict:
        vals = [getattr(record, attr) for record in records]
        if any(value is True for value in vals):
            return Verdict.FAIL
        if all(value is False for value in vals):
            return Verdict.PASS
        if any(value is False for value in vals):
            return Verdict.PARTIAL
        return Verdict.UNDETERMINED

    def positive_status(attr: str) -> Verdict:
        vals = [getattr(record, attr) for record in records]
        if any(value is False for value in vals):
            return Verdict.FAIL
        if all(value is True for value in vals):
            return Verdict.PASS
        if any(value is True for value in vals):
            return Verdict.PARTIAL
        return Verdict.UNDETERMINED

    target = leakage_status("target_leakage")
    search = leakage_status("search_path_leakage")
    ledger = positive_status("all_attempts_logged")
    stopping = positive_status("stopping_rule_recorded")
    statuses = (target, search, ledger, stopping)
    if Verdict.FAIL in statuses:
        overall = Verdict.FAIL
    elif all(status is Verdict.PASS for status in statuses):
        overall = Verdict.PASS
    elif any(status is Verdict.PASS for status in statuses):
        overall = Verdict.PARTIAL
    else:
        overall = Verdict.UNDETERMINED

    reasons = []
    if target is Verdict.FAIL:
        reasons.append("NO_TARGET_LEAKAGE violated")
    if search is Verdict.FAIL:
        reasons.append("NO_HIDDEN_SEARCH_PATH_LEAKAGE violated")
    if ledger is Verdict.FAIL:
        reasons.append("search ledger incomplete")
    if stopping is Verdict.FAIL:
        reasons.append("search stopping rule missing")
    return IntegrityReport(target, search, ledger, stopping, overall, tuple(reasons))


def _core(candidate: CandidateSystem) -> LevelResult:
    predicates: dict[str, Optional[bool]] = {
        "W_tau_nonempty": None,
        "projection_invariant": None,
        "designated_witness_valid": None,
    }
    if candidate.states is None or candidate.transition is None:
        return _level(predicates, "state or transition data missing")

    states = tuple(candidate.states)
    if any(state not in candidate.transition for state in states):
        return _level(predicates, "transition incomplete on E")

    moved = [x for x in states if candidate.transition[x] != x]
    predicates["W_tau_nonempty"] = bool(moved)

    if candidate.projection is None:
        return _level(predicates, "projection data missing")
    if any(state not in candidate.projection for state in states):
        return _level(predicates, "projection incomplete on E")
    if any(candidate.transition[x] not in candidate.projection for x in states):
        predicates["projection_invariant"] = False
    else:
        predicates["projection_invariant"] = all(
            candidate.projection[candidate.transition[x]] == candidate.projection[x]
            for x in states
        )

    witness = candidate.witness
    if witness is None:
        predicates["designated_witness_valid"] = None
    elif witness not in states or candidate.transition.get(witness) is None:
        predicates["designated_witness_valid"] = False
    else:
        target = candidate.transition[witness]
        predicates["designated_witness_valid"] = bool(
            target != witness
            and target in candidate.projection
            and candidate.projection[target] == candidate.projection[witness]
        )
    return _level(predicates)


def _nd_v1(candidate: CandidateSystem, spec: PathSpec) -> Optional[bool]:
    policy = spec.nd_policy
    if policy is None:
        return None
    if policy.policy_id != ND_POLICY_V1:
        return False
    if policy.preregistered is not True:
        return False
    if not policy.required_relations:
        return False
    if candidate.states is None or candidate.transition is None or spec.outgoing is None:
        return None
    if spec.intermediate_states is None:
        return None

    allowed = set(spec.intermediate_states)
    witness = candidate.witness
    witness_image = spec.outgoing.get(witness) if witness is not None else None
    witnessed = False

    for relation_name in policy.required_relations:
        edges = spec.relations.get(relation_name)
        if not edges:
            return False
        edge_set = set(edges)
        if any(a not in allowed or b not in allowed or a == b for a, b in edges):
            return False
        for x in candidate.states:
            tx = candidate.transition.get(x)
            if tx is None or x not in spec.outgoing or tx not in spec.outgoing:
                return None
            if tx == x:
                continue
            lifted = (spec.outgoing[x], spec.outgoing[tx])
            if lifted not in edge_set:
                return False
            if witness_image is not None and witness_image in lifted:
                witnessed = True
    return witnessed


def _path(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.path
    predicates: dict[str, Optional[bool]] = {
        "admissible_path_exists": None,
        "anchor_connected": None,
        "typed_intermediate": None,
        "composition_equals_tau": None,
        "ND_preregistered_and_nontrivial": None,
    }
    if spec is None:
        return _level(predicates, "Kpath not evaluated")
    predicates["admissible_path_exists"] = spec.exists
    if spec.exists is False:
        return _level(predicates, "bounded search found no admissible path")
    predicates["anchor_connected"] = (
        None
        if candidate.anchor_id is None or spec.anchor_id is None
        else spec.anchor_id == candidate.anchor_id
    )

    if candidate.states is not None and spec.intermediate_states is not None and spec.outgoing is not None:
        allowed = set(spec.intermediate_states)
        if all(x in spec.outgoing for x in candidate.states):
            predicates["typed_intermediate"] = all(spec.outgoing[x] in allowed for x in candidate.states)

    if (
        candidate.states is not None
        and candidate.transition is not None
        and spec.outgoing is not None
        and spec.returning is not None
        and all(x in spec.outgoing for x in candidate.states)
    ):
        ys = [spec.outgoing[x] for x in candidate.states]
        if all(y in spec.returning for y in ys) and all(x in candidate.transition for x in candidate.states):
            predicates["composition_equals_tau"] = all(
                spec.returning[spec.outgoing[x]] == candidate.transition[x]
                for x in candidate.states
            )

    predicates["ND_preregistered_and_nontrivial"] = _nd_v1(candidate, spec)
    return _level(predicates)


def _composition_lookup(entries: Sequence[tuple[str, str, str]]) -> dict[tuple[str, str], str]:
    return {(a, b): c for a, b, c in entries}


def _graded(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.graded
    predicates: dict[str, Optional[bool]] = {
        "graded_path_exists": None,
        "anchor_connected": None,
        "same_traversal_channels": None,
        "rho_monoid_valid": None,
        "h_monoid_valid": None,
        "path_composition_defined": None,
        "rho_respects_composition": None,
        "h_respects_composition": None,
        "local_relational_closure": None,
        "global_displacement_nontrivial": None,
    }
    if spec is None:
        return _level(predicates, "Kgraded not evaluated")
    predicates["graded_path_exists"] = spec.exists
    if spec.exists is False:
        return _level(predicates, "no qualifying graded path")

    predicates["anchor_connected"] = (
        None
        if candidate.anchor_id is None or spec.anchor_id is None
        else spec.anchor_id == candidate.anchor_id
    )
    if candidate.path is not None and spec.gamma_parts is not None:
        if candidate.path.out_path_id is None or candidate.path.return_path_id is None:
            predicates["same_traversal_channels"] = None
        else:
            predicates["same_traversal_channels"] = spec.gamma_parts == (
                candidate.path.out_path_id,
                candidate.path.return_path_id,
            )

    if spec.rho_monoid is not None:
        predicates["rho_monoid_valid"] = spec.rho_monoid.validate()
    if spec.h_monoid is not None:
        predicates["h_monoid_valid"] = spec.h_monoid.validate()

    if spec.gamma_parts is not None and spec.gamma is not None:
        lookup = _composition_lookup(spec.path_compositions)
        predicates["path_composition_defined"] = lookup.get(spec.gamma_parts) == spec.gamma

    if (
        spec.gamma_parts is not None
        and spec.gamma is not None
        and spec.rho_labels is not None
        and spec.rho_monoid is not None
    ):
        a, b = spec.gamma_parts
        if all(p in spec.rho_labels for p in (a, b, spec.gamma)):
            combined = spec.rho_monoid.combine(spec.rho_labels[a], spec.rho_labels[b])
            predicates["rho_respects_composition"] = combined == spec.rho_labels[spec.gamma]

    if (
        spec.gamma_parts is not None
        and spec.gamma is not None
        and spec.h_labels is not None
        and spec.h_monoid is not None
    ):
        a, b = spec.gamma_parts
        if all(p in spec.h_labels for p in (a, b, spec.gamma)):
            combined = spec.h_monoid.combine(spec.h_labels[a], spec.h_labels[b])
            predicates["h_respects_composition"] = combined == spec.h_labels[spec.gamma]

    if (
        spec.identity_path is not None
        and spec.gamma is not None
        and spec.rho_labels is not None
        and spec.identity_path in spec.rho_labels
        and spec.gamma in spec.rho_labels
    ):
        predicates["local_relational_closure"] = (
            spec.rho_labels[spec.gamma] == spec.rho_labels[spec.identity_path]
        )

    if (
        spec.identity_path is not None
        and spec.gamma is not None
        and spec.h_labels is not None
        and spec.identity_path in spec.h_labels
        and spec.gamma in spec.h_labels
    ):
        predicates["global_displacement_nontrivial"] = (
            spec.h_labels[spec.gamma] != spec.h_labels[spec.identity_path]
        )
    return _level(predicates)


def _ch(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.ch
    predicates: dict[str, Optional[bool]] = {
        "qualifying_pair_exists": None,
        "anchor_connected": None,
        "Phi_preregistered": None,
        "internal_equivalence_preregistered": None,
        "internally_inequivalent": None,
        "same_realization": None,
        "Phi_discriminative": None,
        "null_experiment_preregistered": None,
        "null_pairs_valid": None,
        "null_search_budget_respected": None,
        "null_equality_rule_fixed": None,
        "null_selection_procedure_fixed": None,
        "null_collision_small": None,
    }
    if spec is None:
        return _level(predicates, "KCH not evaluated")
    predicates["qualifying_pair_exists"] = spec.exists
    if spec.exists is False:
        return _level(predicates, "no qualifying CH pair")

    predicates["anchor_connected"] = (
        None
        if candidate.anchor_id is None or spec.anchor_id is None
        else spec.anchor_id == candidate.anchor_id
    )
    predicates["Phi_preregistered"] = spec.phi_preregistered
    predicates["internal_equivalence_preregistered"] = spec.equivalence_preregistered

    if spec.pair is not None and spec.internal_classes is not None:
        a, b = spec.pair
        if a in spec.internal_classes and b in spec.internal_classes:
            predicates["internally_inequivalent"] = spec.internal_classes[a] != spec.internal_classes[b]
    if spec.pair is not None and spec.realization is not None:
        a, b = spec.pair
        if a in spec.realization and b in spec.realization:
            predicates["same_realization"] = spec.realization[a] == spec.realization[b]
    if spec.paths is not None and spec.realization is not None and all(p in spec.realization for p in spec.paths):
        predicates["Phi_discriminative"] = len({spec.realization[p] for p in spec.paths}) > 1

    exp = spec.collision_experiment
    if exp is None:
        return _level(predicates, "collision experiment missing")
    predicates["null_experiment_preregistered"] = exp.preregistered
    predicates["null_equality_rule_fixed"] = None if exp.equality_rule is None else exp.equality_rule == "EXACT"
    predicates["null_selection_procedure_fixed"] = (
        None if exp.selection_procedure is None else exp.selection_procedure == "FIXED_PAIR"
    )

    if exp.null_pairs is not None and spec.paths is not None and spec.internal_classes is not None:
        paths = set(spec.paths)
        predicates["null_pairs_valid"] = all(
            a in paths
            and b in paths
            and a in spec.internal_classes
            and b in spec.internal_classes
            and spec.internal_classes[a] != spec.internal_classes[b]
            for a, b in exp.null_pairs
        )
    if exp.null_pairs is not None and exp.search_budget is not None:
        predicates["null_search_budget_respected"] = exp.search_budget == len(exp.null_pairs)

    if (
        exp.null_pairs is not None
        and exp.max_collision_probability is not None
        and predicates["null_pairs_valid"] is True
        and spec.realization is not None
        and all(a in spec.realization and b in spec.realization for a, b in exp.null_pairs)
        and len(exp.null_pairs) > 0
    ):
        collisions = sum(spec.realization[a] == spec.realization[b] for a, b in exp.null_pairs)
        rate = Fraction(collisions, len(exp.null_pairs))
        predicates["null_collision_small"] = float(rate) <= exp.max_collision_probability
    return _level(predicates)


def _across(candidate: CandidateSystem) -> LevelResult:
    spec = candidate.across
    predicates: dict[str, Optional[bool]] = {
        "adapter_exists": None,
        "source_anchor_connected": None,
        "target_through_KCH_passes": None,
        "state_map_total": None,
        "projection_commutes": None,
        "transition_commutes": None,
        "outgoing_commutes": None,
        "return_commutes": None,
        "designated_movement_preserved": None,
        "path_map_total": None,
        "rho_labels_commute": None,
        "h_labels_commute": None,
        "CH_pair_compatible": None,
        "adapter_preregistered": None,
        "heldout_pass": None,
        "low_complexity": None,
    }
    if spec is None:
        return _level(predicates, "KACROSS not evaluated")
    predicates["adapter_exists"] = spec.exists
    if spec.exists is False:
        return _level(predicates, "no admissible ACROSS adapter")
    target = spec.target
    if target is None:
        return _level(predicates, "target K structure missing")

    if candidate.anchor_id is not None and spec.anchor_map is not None and target.anchor_id is not None:
        predicates["source_anchor_connected"] = spec.anchor_map.get(candidate.anchor_id) == target.anchor_id

    target_result = detect(target)
    predicates["target_through_KCH_passes"] = all(
        target_result.levels[level].verdict is Verdict.PASS
        for level in ("Kc", "Kp", "Kg", "KCH")
    )

    predicates["adapter_preregistered"] = spec.adapter_preregistered
    predicates["heldout_pass"] = spec.heldout_pass
    predicates["low_complexity"] = spec.low_complexity

    if candidate.states is not None and spec.state_map is not None:
        predicates["state_map_total"] = all(x in spec.state_map for x in candidate.states)

    if (
        candidate.states is not None
        and candidate.projection is not None
        and target.projection is not None
        and spec.state_map is not None
        and spec.base_map is not None
        and all(x in candidate.projection and x in spec.state_map for x in candidate.states)
    ):
        predicates["projection_commutes"] = all(
            candidate.projection[x] in spec.base_map
            and spec.state_map[x] in target.projection
            and spec.base_map[candidate.projection[x]] == target.projection[spec.state_map[x]]
            for x in candidate.states
        )

    if (
        candidate.states is not None
        and candidate.transition is not None
        and target.transition is not None
        and spec.state_map is not None
        and all(x in candidate.transition and x in spec.state_map for x in candidate.states)
    ):
        predicates["transition_commutes"] = all(
            candidate.transition[x] in spec.state_map
            and spec.state_map[x] in target.transition
            and spec.state_map[candidate.transition[x]] == target.transition[spec.state_map[x]]
            for x in candidate.states
        )

    if (
        candidate.path is not None
        and target.path is not None
        and candidate.states is not None
        and candidate.path.outgoing is not None
        and target.path.outgoing is not None
        and spec.state_map is not None
        and spec.intermediate_map is not None
        and all(x in candidate.path.outgoing and x in spec.state_map for x in candidate.states)
    ):
        predicates["outgoing_commutes"] = all(
            candidate.path.outgoing[x] in spec.intermediate_map
            and spec.state_map[x] in target.path.outgoing
            and spec.intermediate_map[candidate.path.outgoing[x]] == target.path.outgoing[spec.state_map[x]]
            for x in candidate.states
        )

    if (
        candidate.path is not None
        and target.path is not None
        and candidate.path.intermediate_states is not None
        and candidate.path.returning is not None
        and target.path.returning is not None
        and spec.state_map is not None
        and spec.intermediate_map is not None
    ):
        ys = candidate.path.intermediate_states
        predicates["return_commutes"] = all(
            y in candidate.path.returning
            and y in spec.intermediate_map
            and candidate.path.returning[y] in spec.state_map
            and spec.intermediate_map[y] in target.path.returning
            and spec.state_map[candidate.path.returning[y]] == target.path.returning[spec.intermediate_map[y]]
            for y in ys
        )

    if (
        candidate.witness is not None
        and candidate.transition is not None
        and spec.state_map is not None
        and candidate.witness in candidate.transition
        and candidate.witness in spec.state_map
        and candidate.transition[candidate.witness] in spec.state_map
    ):
        predicates["designated_movement_preserved"] = (
            spec.state_map[candidate.transition[candidate.witness]] != spec.state_map[candidate.witness]
            and (target.witness is None or spec.state_map[candidate.witness] == target.witness)
        )

    if candidate.graded is not None and candidate.graded.paths is not None and spec.path_map is not None:
        predicates["path_map_total"] = all(path in spec.path_map for path in candidate.graded.paths)

    if (
        candidate.graded is not None
        and target.graded is not None
        and candidate.graded.paths is not None
        and candidate.graded.rho_labels is not None
        and target.graded.rho_labels is not None
        and spec.path_map is not None
        and spec.rho_label_map is not None
    ):
        predicates["rho_labels_commute"] = all(
            path in candidate.graded.rho_labels
            and path in spec.path_map
            and candidate.graded.rho_labels[path] in spec.rho_label_map
            and spec.path_map[path] in target.graded.rho_labels
            and spec.rho_label_map[candidate.graded.rho_labels[path]]
            == target.graded.rho_labels[spec.path_map[path]]
            for path in candidate.graded.paths
        )

    if (
        candidate.graded is not None
        and target.graded is not None
        and candidate.graded.paths is not None
        and candidate.graded.h_labels is not None
        and target.graded.h_labels is not None
        and spec.path_map is not None
        and spec.h_label_map is not None
    ):
        predicates["h_labels_commute"] = all(
            path in candidate.graded.h_labels
            and path in spec.path_map
            and candidate.graded.h_labels[path] in spec.h_label_map
            and spec.path_map[path] in target.graded.h_labels
            and spec.h_label_map[candidate.graded.h_labels[path]]
            == target.graded.h_labels[spec.path_map[path]]
            for path in candidate.graded.paths
        )

    if (
        candidate.ch is not None
        and target.ch is not None
        and candidate.ch.pair is not None
        and target.ch.pair is not None
        and spec.path_map is not None
    ):
        a, b = candidate.ch.pair
        if a in spec.path_map and b in spec.path_map:
            predicates["CH_pair_compatible"] = (
                spec.path_map[a],
                spec.path_map[b],
            ) == target.ch.pair
    return _level(predicates)


def _propagate(raw: Mapping[str, LevelResult]) -> dict[str, LevelResult]:
    result: dict[str, LevelResult] = {}
    prior: list[tuple[str, Verdict]] = []
    for level in LEVELS:
        independent = raw[level]
        prior_failures = [name for name, verdict in prior if verdict is Verdict.FAIL]
        prior_incomplete = [
            name for name, verdict in prior if verdict in (Verdict.PARTIAL, Verdict.UNDETERMINED)
        ]
        verdict = independent.independent_verdict
        prereq_reasons: list[str] = []

        if prior_failures:
            verdict = Verdict.FAIL
            prereq_reasons.append("failed prerequisite(s): " + ", ".join(prior_failures))
        elif verdict is Verdict.PASS and prior_incomplete:
            verdict = Verdict.PARTIAL
            prereq_reasons.append("incomplete prerequisite(s): " + ", ".join(prior_incomplete))

        result[level] = LevelResult(
            independent.independent_verdict,
            verdict,
            independent.predicates,
            independent.reasons,
            tuple(prereq_reasons),
        )
        prior.append((level, verdict))
    return result


def detect(candidate: CandidateSystem) -> DetectorResult:
    raw = {
        "Kc": _core(candidate),
        "Kp": _path(candidate),
        "Kg": _graded(candidate),
        "KCH": _ch(candidate),
        "KA": _across(candidate),
    }
    return DetectorResult(candidate.name, DETECTOR_SPEC_VERSION, _propagate(raw), _integrity(candidate))


def _monoid_to_data(m: Optional[FiniteMonoid]) -> Optional[dict[str, Any]]:
    return None if m is None else {"elements": list(m.elements), "identity": m.identity, "table": [list(x) for x in m.table]}


def _monoid_from_data(d: Optional[Mapping[str, Any]]) -> Optional[FiniteMonoid]:
    return None if d is None else FiniteMonoid(tuple(d["elements"]), d["identity"], tuple(tuple(x) for x in d["table"]))


def candidate_to_data(candidate: CandidateSystem) -> dict[str, Any]:
    def provenance_data() -> dict[str, Any]:
        return {key: asdict(value) for key, value in candidate.provenance.items()}

    path = None
    if candidate.path is not None:
        p = candidate.path
        path = {
            "exists": p.exists,
            "anchor_id": p.anchor_id,
            "intermediate_states": None if p.intermediate_states is None else list(p.intermediate_states),
            "outgoing": None if p.outgoing is None else dict(p.outgoing),
            "returning": None if p.returning is None else dict(p.returning),
            "relations": {k: [list(e) for e in v] for k, v in p.relations.items()},
            "nd_policy": None if p.nd_policy is None else asdict(p.nd_policy),
            "out_path_id": p.out_path_id,
            "return_path_id": p.return_path_id,
        }

    graded = None
    if candidate.graded is not None:
        g = candidate.graded
        graded = {
            "exists": g.exists,
            "anchor_id": g.anchor_id,
            "paths": None if g.paths is None else list(g.paths),
            "identity_path": g.identity_path,
            "gamma": g.gamma,
            "gamma_parts": None if g.gamma_parts is None else list(g.gamma_parts),
            "path_compositions": [list(x) for x in g.path_compositions],
            "rho_labels": None if g.rho_labels is None else dict(g.rho_labels),
            "h_labels": None if g.h_labels is None else dict(g.h_labels),
            "rho_monoid": _monoid_to_data(g.rho_monoid),
            "h_monoid": _monoid_to_data(g.h_monoid),
        }

    ch = None
    if candidate.ch is not None:
        c = candidate.ch
        exp = None if c.collision_experiment is None else {
            **asdict(c.collision_experiment),
            "null_pairs": None if c.collision_experiment.null_pairs is None else [list(x) for x in c.collision_experiment.null_pairs],
        }
        ch = {
            "exists": c.exists,
            "anchor_id": c.anchor_id,
            "paths": None if c.paths is None else list(c.paths),
            "internal_classes": None if c.internal_classes is None else dict(c.internal_classes),
            "realization": None if c.realization is None else dict(c.realization),
            "pair": None if c.pair is None else list(c.pair),
            "phi_preregistered": c.phi_preregistered,
            "equivalence_preregistered": c.equivalence_preregistered,
            "collision_experiment": exp,
        }

    across = None
    if candidate.across is not None:
        a = candidate.across
        across = {
            "exists": a.exists,
            "target": None if a.target is None else candidate_to_data(a.target),
            "state_map": None if a.state_map is None else dict(a.state_map),
            "base_map": None if a.base_map is None else dict(a.base_map),
            "intermediate_map": None if a.intermediate_map is None else dict(a.intermediate_map),
            "path_map": None if a.path_map is None else dict(a.path_map),
            "rho_label_map": None if a.rho_label_map is None else dict(a.rho_label_map),
            "h_label_map": None if a.h_label_map is None else dict(a.h_label_map),
            "anchor_map": None if a.anchor_map is None else dict(a.anchor_map),
            "adapter_preregistered": a.adapter_preregistered,
            "heldout_pass": a.heldout_pass,
            "low_complexity": a.low_complexity,
        }

    return {
        "name": candidate.name,
        "states": None if candidate.states is None else list(candidate.states),
        "projection": None if candidate.projection is None else dict(candidate.projection),
        "transition": None if candidate.transition is None else dict(candidate.transition),
        "witness": candidate.witness,
        "anchor_id": candidate.anchor_id,
        "path": path,
        "graded": graded,
        "ch": ch,
        "across": across,
        "provenance": provenance_data(),
        "scope_note": candidate.scope_note,
    }


def candidate_from_data(data: Mapping[str, Any]) -> CandidateSystem:
    p = data.get("path")
    path = None
    if p is not None:
        nd = p.get("nd_policy")
        path = PathSpec(
            p.get("exists"),
            p.get("anchor_id"),
            None if p.get("intermediate_states") is None else tuple(p["intermediate_states"]),
            p.get("outgoing"),
            p.get("returning"),
            {k: tuple(tuple(e) for e in v) for k, v in p.get("relations", {}).items()},
            None if nd is None else NDPolicy(nd["policy_id"], nd.get("preregistered"), tuple(nd.get("required_relations", ()))),
            p.get("out_path_id"),
            p.get("return_path_id"),
        )

    g = data.get("graded")
    graded = None
    if g is not None:
        graded = GradedSpec(
            g.get("exists"),
            g.get("anchor_id"),
            None if g.get("paths") is None else tuple(g["paths"]),
            g.get("identity_path"),
            g.get("gamma"),
            None if g.get("gamma_parts") is None else tuple(g["gamma_parts"]),
            tuple(tuple(x) for x in g.get("path_compositions", ())),
            g.get("rho_labels"),
            g.get("h_labels"),
            _monoid_from_data(g.get("rho_monoid")),
            _monoid_from_data(g.get("h_monoid")),
        )

    c = data.get("ch")
    ch = None
    if c is not None:
        exp = c.get("collision_experiment")
        collision = None
        if exp is not None:
            collision = CollisionExperiment(
                exp.get("preregistered"),
                exp.get("equality_rule"),
                exp.get("selection_procedure"),
                exp.get("search_budget"),
                None if exp.get("null_pairs") is None else tuple(tuple(x) for x in exp["null_pairs"]),
                exp.get("max_collision_probability"),
            )
        ch = CHSpec(
            c.get("exists"),
            c.get("anchor_id"),
            None if c.get("paths") is None else tuple(c["paths"]),
            c.get("internal_classes"),
            c.get("realization"),
            None if c.get("pair") is None else tuple(c["pair"]),
            c.get("phi_preregistered"),
            c.get("equivalence_preregistered"),
            collision,
        )

    a = data.get("across")
    across = None
    if a is not None:
        across = AcrossSpec(
            a.get("exists"),
            None if a.get("target") is None else candidate_from_data(a["target"]),
            a.get("state_map"),
            a.get("base_map"),
            a.get("intermediate_map"),
            a.get("path_map"),
            a.get("rho_label_map"),
            a.get("h_label_map"),
            a.get("anchor_map"),
            a.get("adapter_preregistered"),
            a.get("heldout_pass"),
            a.get("low_complexity"),
        )

    provenance = {
        key: Provenance(
            tuple(value.get("assumptions", ())),
            tuple(value.get("search_steps", ())),
            value.get("target_leakage"),
            value.get("search_path_leakage"),
            value.get("all_attempts_logged"),
            value.get("stopping_rule_recorded"),
        )
        for key, value in data.get("provenance", {}).items()
    }

    return CandidateSystem(
        data["name"],
        None if data.get("states") is None else tuple(data["states"]),
        data.get("projection"),
        data.get("transition"),
        data.get("witness"),
        data.get("anchor_id"),
        path,
        graded,
        ch,
        across,
        provenance,
        data.get("scope_note"),
    )
