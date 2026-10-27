from __future__ import annotations

from typing import Any

from meridiano_lab.errors import LabError


def evaluate_integrity_gates(
    normalized: dict[str, Any],
    manifest: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-05] Calcola metadati, qualità e checksum.

    Ogni gate restituisce result, reasons ed evidence_refs. Missing e checksum discordi non
    possono diventare PASS.
    """
    raise LabError("todo_05", "Implementare evaluate_integrity_gates.")


def evaluate_authority_gates(
    normalized: dict[str, Any],
    manifest: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-06] Calcola licenza, embargo e approval formali.

    Email e ticket non valgono come approval. Un legal clearance non approvato è CONFLICT.
    """
    raise LabError("todo_06", "Implementare evaluate_authority_gates.")
