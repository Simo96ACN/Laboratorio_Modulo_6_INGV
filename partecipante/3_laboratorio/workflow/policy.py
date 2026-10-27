from __future__ import annotations

from typing import Any

from meridiano_lab.errors import LabError


def propose_decisions(
    deterministic_gates: dict[str, Any],
    ai_results: dict[str, Any],
    normalized: dict[str, Any],
    design: dict[str, Any],
) -> dict[str, Any]:
    """[TODO-09] Produce una proposta per dataset senza autorizzare azioni.

    Precedenza minima: CONFLICT e UNKNOWN seguono la strategia congelata; FAIL non pubblica;
    Se ai_delegation.approval_requests è enabled, ogni proposta include approval_requests:
    lista di oggetti {scope, reason} per gli scope publication_owner/publication_steward
    privi di approvazione valida; [] quando non serve una richiesta. Il runtime crea task
    simulati e, dopo una risposta umana di ruolo, richiama gate e questa policy.
    Una risposta di pubblicazione non sana qualità, diritti, embargo o sensibilità.
    tutti PASS possono produrre PUBBLICA o PUBBLICA_CON_CONDIZIONI. SENSITIVE diventa
    CONFLICT. Nessuna scelta può rimuovere gli hard stop.
    """
    raise LabError("todo_09", "Implementare propose_decisions.")
