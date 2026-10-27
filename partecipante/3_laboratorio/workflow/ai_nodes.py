from __future__ import annotations

from typing import Any

from meridiano_lab.errors import LabError


def validate_classify_evidence(
    request: dict[str, Any],
    response: dict[str, Any],
    normalized: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-08] Valida copertura e provenienza della risposta AI.

    Richiedere esattamente un output per dataset e evidence_refs appartenenti allo stesso
    dataset. Applicare anche ai_validation e minimum_independent_evidence dichiarati nel design.
    Restituire un mapping dataset_id -> risultato AI validato.
    """
    raise LabError("todo_08", "Implementare validate_classify_evidence.")
