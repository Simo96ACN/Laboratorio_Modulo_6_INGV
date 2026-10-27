"""Contratto del TODO-01, compilato dal partecipante dopo il freeze."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import LabError
from .utils import read_json

CONFIG_PATH = Path("workflow/agent_config.json")
REQUIRED_TOOLS = {"catalog", "request", "search-evidence", "read-evidence", "submit-draft", "needs-input"}
OPTIONAL_TOOLS = {"status", "check-draft", "approval-requests", "request-approval", "simulate-role-response"}
STOP_CONDITIONS = {"draft_submitted", "needs_input", "budget_exhausted"}


def load_agent_config(root: Path, design: dict[str, Any]) -> dict[str, Any]:
    """Verifica scelte, permessi e confine umano senza chiamare un modello."""
    path = root / CONFIG_PATH
    if not path.is_file():
        raise LabError("agent_config_required", "Completa TODO-01: manca workflow/agent_config.json.")
    config = read_json(path)
    keys = {"execution_mode", "objective", "instructions", "allowed_tools", "max_calls", "stop_conditions", "output_path", "approval_requests"}
    if not isinstance(config, dict) or not keys <= set(config) or set(config) - keys - {"role_response_mode"}:
        raise LabError("agent_config_incomplete", "TODO-01: completa i campi del template, rimuovendo il marker todo.")
    config.setdefault("role_response_mode", "human")
    if config["role_response_mode"] not in {"human", "model_simulated"}:
        raise LabError("agent_config_role_mode", "Scegli human oppure model_simulated: il ruolo reale resta umano.")
    if config["execution_mode"] != design["ai_delegation"]["execution_mode"]:
        raise LabError("agent_config_mode", "TODO-01: modalità diversa dalla spec congelata; non sostituire agent con manual.")
    if config["approval_requests"] != design["ai_delegation"]["approval_requests"]:
        raise LabError("agent_config_approval_mode", "Le richieste di ruolo devono seguire la scelta congelata nella sezione 5.")
    for key in ("objective", "instructions"):
        value = config[key]
        if not isinstance(value, str) or len(value.strip()) < 30 or "[" in value:
            raise LabError("agent_config_incomplete", f"TODO-01: descrivi {key} con un incarico concreto.")
    tools = config["allowed_tools"]
    if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
        raise LabError("agent_config_tools", "allowed_tools deve essere una lista di nomi del catalogo.")
    if len(tools) != len(set(tools)) or not REQUIRED_TOOLS <= set(tools) or set(tools) - REQUIRED_TOOLS - OPTIONAL_TOOLS:
        raise LabError("agent_config_tools", "TODO-01: servono i tool di consultazione, consegna e richiesta di chiarimento; continue/review sono umani.")
    if config["approval_requests"] == "enabled" and not {"approval-requests", "request-approval"} <= set(tools):
        raise LabError("agent_config_tools", "La spec abilita le richieste: includi approval-requests e request-approval.")
    if config["role_response_mode"] == "model_simulated":
        if config["approval_requests"] != "enabled" or "simulate-role-response" not in tools:
            raise LabError("agent_config_role_mode", "La simulazione richiede richieste enabled e il tool simulate-role-response.")
    elif "simulate-role-response" in tools:
        raise LabError("agent_config_role_mode", "Il tool simulate-role-response richiede la scelta esplicita model_simulated.")
    budget = config["max_calls"]
    if type(budget) is not int or not 1 <= budget <= 40:
        raise LabError("agent_config_budget", "TODO-01: max_calls deve essere un intero fra 1 e 40.")
    stops = config["stop_conditions"]
    if not isinstance(stops, list) or not all(isinstance(stop, str) for stop in stops) or set(stops) != STOP_CONDITIONS or len(stops) != 3:
        raise LabError("agent_config_stops", "TODO-01: prevedi draft_submitted, needs_input e budget_exhausted.")
    if config["output_path"] != "agent/draft.txt":
        raise LabError("agent_config_output", "TODO-01: la sola uscita operativa ammessa è agent/draft.txt del run.")
    return config


def render_agent_card(config: dict[str, Any]) -> str:
    """Rende visibile la delega appena configurata, prima degli altri nodi."""
    tools = "\n".join(f"- {name}" for name in config["allowed_tools"])
    return (
        "# Il tuo incarico per l'agente\n\n"
        f"Modalità: {config['execution_mode']}\n\n"
        f"**Risultato che gli affidi:** {config['objective']}\n\n"
        f"**Come deve lavorare:** {config['instructions']}\n\n"
        f"**Strumenti che gli concedi:**\n\n{tools}\n\n"
        f"**Limite delle consultazioni:** {config['max_calls']}; il runtime può applicare un tetto più basso.\n\n"
        f"**Richieste simulate ai ruoli:** {config['approval_requests']}. Modalità risposta: {config.get('role_response_mode', 'human')}.\n\n"
        "**Nel processo reale:** il responsabile è una persona. model_simulated è soltanto un gioco di ruolo didattico e non vale come approvazione reale.\n\n"
        f"**Quando si ferma:** {', '.join(config['stop_conditions'])}.\n\n"
        "**Che cosa riprendi tu:** controllo delle risposte (umane o simulate dal modello), importazione, verifica dei gate e review finale.\n\n"
        "Questa è una configurazione verificata, non una prova di esecuzione del modello.\n"
        "Prevedi una richiesta legittima e una che l'agente deve rifiutare; verificane l'esito nella prova finale.\n"
    )
