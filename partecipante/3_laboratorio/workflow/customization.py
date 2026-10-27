from __future__ import annotations

from typing import Any

from meridiano_lab.errors import LabError


def customize_proposals(
    proposals: dict[str, Any],
    normalized: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-11] Applica una personalizzazione significativa senza indebolire gli hard stop.

    Usa soltanto selected_dimensions del WorkflowDesign congelato. Il comportamento deve
    restare indipendente dagli ID baseline, citare la scelta applicata e avere almeno una
    challenge discriminante.
    """
    raise LabError("todo_11", "Implementare la personalizzazione selezionata.")
