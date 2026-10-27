from __future__ import annotations

from typing import Any, Protocol


class WorkflowImplementation(Protocol):
    """Confine fra infrastruttura fornita e logica progettata dal partecipante."""

    implementation_id: str

    def normalize(
        self,
        raw_bundle: dict[str, Any],
        manifest: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def evaluate_gates(
        self,
        normalized: dict[str, Any],
        manifest: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def validate_ai_outputs(
        self,
        request: dict[str, Any],
        response: dict[str, Any],
        normalized: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def decide(
        self,
        deterministic_gates: dict[str, Any],
        ai_results: dict[str, Any],
        normalized: dict[str, Any],
        design: dict[str, Any],
    ) -> dict[str, Any]:
        ...
