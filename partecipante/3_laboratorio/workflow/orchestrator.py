from __future__ import annotations

from typing import Any

from meridiano_lab.errors import LabError

from .ai_nodes import validate_classify_evidence
from .customization import customize_proposals
from .gates import evaluate_authority_gates, evaluate_integrity_gates
from .mappings import (
    canonicalize_dataset,
    map_licenses,
    map_metadata,
    map_quality,
    map_registry,
    map_text_evidence,
)
from .policy import propose_decisions


def build_normalized_bundle(
    raw_bundle: dict[str, Any],
    manifest: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-10] Compone i mapping in un normalized_bundle.

    Creare una vista per ciascun manifest.dataset_ids, integrare ticket e calendario senza
    attribuire loro autorità impropria, ordinare le evidenze e registrare le statistiche di
    deduplicazione. Non calcolare gate o decisioni in questa funzione.
    """
    raise LabError("todo_10", "Implementare build_normalized_bundle.")


class ParticipantWorkflow:
    implementation_id = "participant-workflow-2.0-spec-driven"

    def normalize(
        self,
        raw_bundle: dict[str, Any],
        manifest: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        return build_normalized_bundle(raw_bundle, manifest, design)

    def evaluate_gates(
        self,
        normalized: dict[str, Any],
        manifest: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        integrity = evaluate_integrity_gates(normalized, manifest, design)
        authority = evaluate_authority_gates(normalized, manifest, design)
        if set(integrity) != set(authority):
            raise LabError("gate_coverage", "Le due famiglie di gate non coincidono.")
        return {
            dataset_id: {**integrity[dataset_id], **authority[dataset_id]}
            for dataset_id in normalized["dataset_ids"]
        }

    def validate_ai_outputs(
        self,
        request: dict[str, Any],
        response: dict[str, Any],
        normalized: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        return validate_classify_evidence(request, response, normalized, design)

    def decide(
        self,
        deterministic_gates: dict[str, Any],
        ai_results: dict[str, Any],
        normalized: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        proposals = propose_decisions(
            deterministic_gates,
            ai_results,
            normalized,
            design,
        )
        return customize_proposals(proposals, normalized, design)


def create_participant_workflow(
    design: dict[str, Any] | None = None,
) -> ParticipantWorkflow:
    # Il design viene passato anche a ogni nodo dall'infrastruttura. Accettarlo
    # nella factory rende esplicito il contratto per chat AI e participant code.
    if design is None:
        raise LabError(
            "spec_not_loaded",
            "Caricare il WorkflowDesign prima di creare il workflow.",
        )
    return ParticipantWorkflow()
