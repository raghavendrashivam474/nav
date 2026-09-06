"""
NAV v2 — S25: Evidence Synthesis Engine.

Deterministic synthesis of S24 Evidence items into structured Findings.
Consumes explicit S24 EvidenceRelation objects — does NOT perform NLP,
semantic comparison, or LLM-based reasoning.

S25 §5: Must not manufacture certainty the evidence does not justify.
S25 §12: Deterministic — same input produces same output.
S25 §13: No automatic NLP contradiction detection.
S25 §14: No arbitrary numerical weighting.
S25 §17: No ghost evidence — failed acquisition cannot enter synthesis.
S25 §18: Empty evidence must not produce a successful finding.
S25 §19: Conflicts are represented honestly, not resolved.
"""

from __future__ import annotations

from uuid import uuid4

from capabilities.evidence.service import EvidenceService
from core.contracts.evidence import EvidenceRelation, RelationType
from core.contracts.finding import Finding, FindingState

# Relation types that indicate agreement between evidence items.
_SUPPORTING_RELATIONS: frozenset[RelationType] = frozenset(
    {RelationType.SUPPORTS, RelationType.CORROBORATES}
)

# Relation types that indicate disagreement.
_CONTRADICTING_RELATIONS: frozenset[RelationType] = frozenset(
    {RelationType.CONTRADICTS}
)


class EvidenceSynthesizer:
    """
    Deterministic evidence synthesis engine.

    Takes a bounded set of S24 Evidence items (by ID) and their explicit
    S24 EvidenceRelation objects, and produces a structured Finding.

    Does NOT:
    - Use LLMs or NLP
    - Perform semantic comparison
    - Assign numerical confidence scores
    - Resolve conflicts
    - Manufacture certainty

    Does:
    - Consume explicit S24 relations
    - Classify evidence as supporting or contradicting
    - Represent conflicts honestly
    - Preserve provenance through evidence_basis
    - Handle empty and insufficient evidence explicitly
    """

    def __init__(self, evidence_service: EvidenceService) -> None:
        self._service = evidence_service

    def synthesize(
        self,
        evidence_ids: list[str],
        claim: str,
    ) -> Finding:
        """
        Synthesize a Finding from a bounded set of evidence items.

        Args:
            evidence_ids: IDs of evidence items to synthesize.
            claim: The claim or question being evaluated.

        Returns:
            A deterministic Finding based on the evidence and its relations.

        Raises:
            ValueError: If claim is empty.
            KeyError: If any evidence_id is not found in the store.
        """
        if not claim or not claim.strip():
            raise ValueError("Synthesis claim must not be empty.")

        # Deduplicate while preserving order
        unique_ids = list(dict.fromkeys(evidence_ids))

        # §18: Handle empty evidence
        if not unique_ids:
            return self._build_finding(
                claim=claim,
                status=FindingState.INSUFFICIENT_EVIDENCE,
                supporting=(),
                contradicting=(),
                evidence_basis=(),
                uncertainty="No evidence was provided for synthesis.",
                synthesis_basis="Empty evidence set — no synthesis possible.",
            )

        # Validate all evidence exists (§17: no ghost evidence)
        for eid in unique_ids:
            if self._service.get_evidence(eid) is None:
                raise KeyError(f"Evidence not found: {eid}")

        # Collect all relations within the evidence set
        internal_relations = self._collect_internal_relations(unique_ids)

        # Classify evidence based on relations
        supporting_ids, contradicting_ids = self._classify_evidence(
            internal_relations
        )

        # Determine finding status
        status = self._determine_status(
            supporting_ids, contradicting_ids
        )

        # Build uncertainty description
        uncertainty = self._build_uncertainty(
            status, supporting_ids, contradicting_ids
        )

        # Build synthesis basis explanation
        synthesis_basis = self._build_synthesis_basis(
            unique_ids, internal_relations, supporting_ids, contradicting_ids
        )

        return self._build_finding(
            claim=claim,
            status=status,
            supporting=tuple(sorted(supporting_ids)),
            contradicting=tuple(sorted(contradicting_ids)),
            evidence_basis=tuple(sorted(unique_ids)),
            uncertainty=uncertainty,
            synthesis_basis=synthesis_basis,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_internal_relations(
        self, evidence_ids: list[str]
    ) -> list[EvidenceRelation]:
        """Collect all relations where both endpoints are in the evidence set."""
        id_set = set(evidence_ids)
        seen: set[str] = set()
        internal: list[EvidenceRelation] = []

        for eid in evidence_ids:
            for rel in self._service.get_relations_for(eid):
                if (
                    rel.source_evidence_id in id_set
                    and rel.target_evidence_id in id_set
                    and rel.relation_id not in seen
                ):
                    internal.append(rel)
                    seen.add(rel.relation_id)

        return internal

    @staticmethod
    def _classify_evidence(
        relations: list[EvidenceRelation],
    ) -> tuple[set[str], set[str]]:
        """
        Classify evidence items based on their relation roles.

        Items participating in SUPPORTS/CORROBORATES → supporting.
        Items participating in CONTRADICTS → contradicting.
        An item can appear in both sets.
        """
        supporting: set[str] = set()
        contradicting: set[str] = set()

        for rel in relations:
            if rel.relation_type in _SUPPORTING_RELATIONS:
                supporting.add(rel.source_evidence_id)
                supporting.add(rel.target_evidence_id)
            elif rel.relation_type in _CONTRADICTING_RELATIONS:
                contradicting.add(rel.source_evidence_id)
                contradicting.add(rel.target_evidence_id)

        return supporting, contradicting

    @staticmethod
    def _determine_status(
        supporting_ids: set[str],
        contradicting_ids: set[str],
    ) -> FindingState:
        """
        Deterministic status from relation classification.

        S25 §12: No arbitrary weighting.
        S25 §19: Contradictions → CONTESTED, not resolved.
        S25 §20: All-supporting → SUPPORTED, not CERTAIN.
        """
        has_contradiction = len(contradicting_ids) > 0
        has_support = len(supporting_ids) > 0

        if has_contradiction:
            return FindingState.CONTESTED
        if has_support:
            return FindingState.SUPPORTED
        return FindingState.INCONCLUSIVE

    @staticmethod
    def _build_uncertainty(
        status: FindingState,
        supporting_ids: set[str],
        contradicting_ids: set[str],
    ) -> str:
        """Build a deterministic uncertainty description."""
        if status == FindingState.INSUFFICIENT_EVIDENCE:
            return "No evidence was provided for synthesis."
        if status == FindingState.INCONCLUSIVE:
            return (
                "Evidence exists but no explicit support or contradiction "
                "relationships have been recorded between the provided items."
            )
        if status == FindingState.SUPPORTED:
            return (
                f"All {len(supporting_ids)} related evidence items support "
                "the claim with no recorded contradictions. "
                "Retrieved evidence does not constitute verified truth."
            )
        # CONTESTED
        return (
            f"Evidence contains {len(supporting_ids)} supporting and "
            f"{len(contradicting_ids)} contradicting items. "
            "The conflict remains unresolved."
        )

    @staticmethod
    def _build_synthesis_basis(
        evidence_ids: list[str],
        relations: list[EvidenceRelation],
        supporting_ids: set[str],
        contradicting_ids: set[str],
    ) -> str:
        """Build a deterministic explanation of the derivation."""
        support_rels = sum(
            1 for r in relations if r.relation_type in _SUPPORTING_RELATIONS
        )
        contradict_rels = sum(
            1 for r in relations if r.relation_type in _CONTRADICTING_RELATIONS
        )
        derived_rels = sum(
            1 for r in relations if r.relation_type == RelationType.DERIVED_FROM
        )

        return (
            f"Synthesized from {len(evidence_ids)} evidence items. "
            f"Internal relations: {len(relations)} total "
            f"({support_rels} supporting, {contradict_rels} contradicting, "
            f"{derived_rels} derived-from). "
            f"Supporting evidence: {len(supporting_ids)} items. "
            f"Contradicting evidence: {len(contradicting_ids)} items."
        )

    @staticmethod
    def _build_finding(
        claim: str,
        status: FindingState,
        supporting: tuple[str, ...],
        contradicting: tuple[str, ...],
        evidence_basis: tuple[str, ...],
        uncertainty: str,
        synthesis_basis: str,
    ) -> Finding:
        """Construct a frozen Finding with a generated ID."""
        return Finding(
            finding_id=str(uuid4()),
            claim=claim,
            status=status,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            uncertainty=uncertainty,
            evidence_basis=evidence_basis,
            synthesis_basis=synthesis_basis,
        )
