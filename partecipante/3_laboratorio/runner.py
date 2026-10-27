#!/usr/bin/env python3
"""CLI human-first del Meridiano Workflow Lab."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from meridiano_lab import LabError, WorkflowLabService
from meridiano_lab.preflight import run_preflight
from meridiano_lab.spec_bridge import freeze_spec, load_frozen_design
from meridiano_lab.text_exchange import render_decision_form
from meridiano_lab.utils import atomic_write_text
from meridiano_lab.utils import path_is_file, read_json
from workflow import create_participant_workflow


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_WORKSPACE = BASE_DIR / "workspace"
DEFAULT_CASE = BASE_DIR / "case"
DEFAULT_PROMPT = BASE_DIR / "workflow" / "prompts" / "classify_evidence.txt"


def emit_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def service(args: argparse.Namespace) -> WorkflowLabService:
    design = load_frozen_design(BASE_DIR)
    return WorkflowLabService(
        args.workspace.resolve(),
        create_participant_workflow(design),
        design,
        participant_root=BASE_DIR,
    )


def resolve_run_id(lab: WorkflowLabService, explicit: str | None) -> str:
    if explicit:
        return explicit
    runs = lab.list_runs()
    if not runs:
        raise LabError("missing_run", "Nessun run disponibile. Esegui prima start.")
    return sorted(runs, key=lambda item: item["created_at"])[-1]["run_id"]


def human_summary(command: str, value: dict[str, Any], open_runs: list[dict[str, Any]] | None = None) -> str:
    if command == "check-agent-config":
        return f"Hai configurato il tuo agente: modalità {value['execution_mode']}; budget massimo {value['max_calls']}. Apri build/agent/il_tuo_agente.md e verifica l'incarico. Ora puoi costruire gli altri nodi; la prova operativa arriverà dopo."
    if command == "prepare-agent":
        return value["start"] + ("\n" + value["warning"] if value.get("warning") else "")
    if command in {"fallback-agent", "stop-agent", "resume-agent", "reopen-agent"}:
        return "\n".join([
            f"Run: {value['run_id']}", f"Sessione operativa: {value['status']}",
            f"Revisione: {value['revision']}; chiamate usate: {value['used']}",
            f"Mandato corrente: {value['mandate_path']}",
            "Il workflow resta in WAITING_FOR_AI; importazione e review spettano alla persona.",
        ])
    if command == "freeze-spec":
        return "\n".join(
            [
                "Spec congelata.",
                f"ID: {value['spec_id']}",
                f"Stato: {value['status']}",
                f"Campi di progetto: {value['design_fields']}",
                f"Campi diario: {value['lab_record_fields']}",
                "Ora apri build/ai/ai_build_brief.txt e parti dal TODO-01: configura il tuo agente prima degli altri nodi.",
            ]
        )
    if command == "preflight":
        lines = [
            "Preflight completato.",
            f"Stato: {value['status']}",
            f"TODO da completare: {value['todo_count']}",
            f"Modalità nodo AI: {value.get('ai_execution_mode') or 'da scegliere nella spec'}",
            f"Configurazione TODO-01: {value['agent_configuration']}",
            (
                f"Spec: {value['spec'].get('spec_id', value['spec'].get('code', '-'))}"
            ),
            "Runtime offline: sì" if value["offline_runtime"] else "Runtime offline: no",
        ]
        environment = value.get("environment", {})
        if not environment.get("long_path_ok", True):
            lines.append(f"ATTENZIONE percorso lungo: {environment.get('hint', '')}")
        return "\n".join(lines)
    if "state" in value:
        # Anche le viste minime usate dai chiamanti di manutenzione restano leggibili.
        view = {"workspace": str(DEFAULT_WORKSPACE), "approval_requests": {}, **value}
        return render_run_map(view, open_runs or [])
    if value.get("kind") == "submission_archive_receipt":
        return "\n".join([
            f"Consegna creata: {value['archive']}",
            f"Run inclusi: {', '.join(value['run_ids'])}",
            f"Artefatti collegati tramite hash: {value['artifacts']}",
        ])
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _shell_path(path: Path) -> str:
    """Percorso breve, quotato come argomento letterale PowerShell se necessario."""
    try:
        text = os.path.relpath(path, Path.cwd())
    except ValueError:
        text = str(path)
    if text == os.pardir or text.startswith(os.pardir + os.sep):
        text = str(path)
    return "'" + text.replace("'", "''") + "'" if any(c.isspace() or c in "'\"`$;&|(){}[]<>" for c in text) else text


def _run_steps(value: dict[str, Any]) -> tuple[list[tuple[str, str, str]], int]:
    """Passi del run (titolo, chi, dove) e indice del passo corrente.

    Lo stato si deduce soltanto da stato del workflow, sessione agente e task:
    nessun nuovo contratto, nessuna scrittura.
    """
    status = value["state"]["status"]
    mode = value.get("ai_execution_mode", "manual")
    session = value.get("agent_session_status")
    tasks = value.get("approval_requests", {})
    if mode == "agent" and session != "FALLBACK":
        steps = [
            ("Avvio del run", "TU", "terminale: start"),
            ("Prepara l'operatore", "TU", "terminale: prepare-agent"),
            ("Classificazione delle evidenze", "OPERATORE", "nuova chat: consegna la bozza"),
            ("Importa la bozza", "TU", "terminale: continue"),
        ]
    else:
        label = "Classificazione (FALLBACK manuale)" if mode == "agent" else "Classificazione (scambio manuale)"
        steps = [
            ("Avvio del run", "TU", "terminale: start"),
            ("Prompt alla chat", "TU", "exchange/prompt.txt"),
            (label, "TU", "exchange/response.txt"),
            ("Importa la risposta", "TU", "terminale: continue"),
        ]
    if tasks.get("enabled"):
        who = "SIMULATORE o TU" if tasks.get("role_response_mode") == "model_simulated" else "TU"
        answered = sum(row["status"] != "PENDING" for row in tasks.get("tasks", []))
        total = len(tasks.get("tasks", []))
        title = f"Risposte ai ruoli ({answered}/{total})" if status != "WAITING_FOR_AI" else "Risposte ai ruoli"
        steps.append((title, who, "nuova chat o terminale: respond-approval"))
    else:
        steps.append(("Risposte ai ruoli: non previste", "-", "-"))
    steps.append(("Review finale", "TU", "decisions.txt + terminale: review"))
    steps.append(("Annota osservazioni", "TU", "agent/EVIDENZE_PARTECIPANTE.md"))

    if status == "WAITING_FOR_AI":
        if mode == "agent" and session != "FALLBACK":
            current = {None: 1, "DRAFT_SUBMITTED": 3}.get(session, 2)
        else:
            current = 2
    elif status == "WAITING_FOR_APPROVAL":
        current = 4 if tasks.get("pending") else 5
    elif status == "COMPLETED":
        current = 6
    else:
        current = 0
    return steps, current


def _next_step(value: dict[str, Any], current: int) -> list[str]:
    state = value["state"]
    run_id = state["run_id"]
    workspace = Path(value["workspace"])
    run_dir = workspace / "runs" / run_id
    ws = _shell_path(workspace)
    runner = f"python runner.py --workspace {ws}"
    session = value.get("agent_session_status")
    tasks = value.get("approval_requests", {})
    if current == 1:
        return [
            "PROSSIMO PASSO - tocca a te, nel terminale:",
            f"  {runner} prepare-agent --run-id {run_id}",
            "Il comando stampa il testo da incollare nella chat dell'operatore.",
        ]
    if current == 2 and session in {"OPEN", "NEEDS_INPUT", "STOPPED"}:
        mandate = run_dir / "agent" / "mandate.txt"
        if session != "OPEN":
            return [
                "PROSSIMO PASSO - tocca a te, nel terminale:",
                f"ATTENZIONE: l'operatore si è fermato ({session}). Leggi la sua richiesta, poi:",
                f"  riprendi:  {runner} resume-agent --run-id {run_id} --reason \"<chiarimento>\"",
                f"  oppure:    {runner} fallback-agent --run-id {run_id} --reason \"<motivo>\"",
                "Dopo la scelta esegui status sullo stesso run e segui il nuovo incarico.",
            ]
        session_path = run_dir / "agent" / "session.json"
        if path_is_file(session_path):
            mandate = run_dir / read_json(session_path).get("mandate_path", "agent/mandate.txt")
        return [
            "PROSSIMO PASSO - tocca all'OPERATORE, in una NUOVA chat aperta sulla cartella del laboratorio.",
            "Incolla questo messaggio:",
            "  ----------------------------------------------------------------",
            "  Leggi AGENTS.md, agent/START_OPERATORE.md e il mandato",
            f"  {mandate}",
            f"  Run autorizzato: {run_id}",
            f"  Workspace: {workspace}",
            "  ----------------------------------------------------------------",
            "Osserva le chiamate ai tool: l'operatore si ferma dopo submit-draft o needs-input.",
            "Poi torna qui ed esegui di nuovo status.",
        ]
    if current == 2:
        return [
            "PROSSIMO PASSO - tocca a te:",
            f"  1) apri {_shell_path(run_dir / 'exchange' / 'prompt.txt')} e incollalo nella chat",
            f"  2) salva la risposta in {_shell_path(run_dir / 'exchange' / 'response.txt')}",
            f"  3) {runner} continue --run-id {run_id}",
        ]
    if current == 3:
        return [
            "PROSSIMO PASSO - tocca a te, nel terminale:",
            f"  1) controlla la bozza in {_shell_path(run_dir / 'agent' / 'draft.txt')}",
            f"  2) {runner} continue --run-id {run_id}",
        ]
    if current == 4:
        pending = [row for row in tasks.get("tasks", []) if row["status"] == "PENDING"]
        lines = ["Richieste ai ruoli in attesa:"]
        lines += [
            f"  {row['task_id']} | {row['dataset_id']} v{row['version']} | {row['target_role']}"
            for row in pending
        ]
        lines.append("")
        if tasks.get("role_response_mode") == "model_simulated":
            lines += [
                "PROSSIMO PASSO - opzione A: il SIMULATORE, in una NUOVA chat. Incolla:",
                "  ----------------------------------------------------------------",
                "  Leggi AGENTS.md e agent/SIMULA_RESPONSABILE.md ed esegui l'incarico.",
                f"  Workspace: {workspace}",
                f"  RUN_ID: {run_id}",
                f"  Task assegnati: {', '.join(row['task_id'] for row in pending)}",
                "  Modello/sessione da dichiarare: <scrivi modello e sessione>",
                "  ----------------------------------------------------------------",
                "Opzione B: rispondi tu nel ruolo, per ogni task:",
            ]
        else:
            lines.append("PROSSIMO PASSO - rispondi tu nel ruolo, per ogni task:")
        lines += [
            f"  {runner} respond-approval --run-id {run_id} --task-id <TASK_ID> --actor \"<nome>\" "
            "--role \"<ruolo del task>\" --decision <APPROVE|REJECT> --reason \"<motivazione>\"",
            "È una risposta di ruolo simulata, distinta dalla review finale: i gate vengono ricalcolati.",
        ]
        return lines
    if current == 5:
        lines = []
        if tasks.get("contains_model_simulated_responses"):
            lines += [
                "Nota: alcune risposte di ruolo vengono dal modello (simulazione didattica),",
                "non sono approvazioni reali. Confronta i gate in approval_reassessment.json.",
                "",
            ]
        lines.append("Proposte del workflow:")
        for dataset_id, decision in value.get("decisions", {}).items():
            stops = ", ".join(decision.get("hard_stops", [])) or ("sì" if decision["hard_stop"] else "nessuno")
            lines.append(f"  {dataset_id}: {decision['proposal']} (hard stop: {stops})")
        return lines + [
            "",
            "PROSSIMO PASSO - tocca a te, la review finale:",
            f"  1) compila {_shell_path(run_dir / 'exchange' / 'decisions.txt')}",
            "     per ogni dataset: DECISIONE APPROVA_PROPOSTA oppure RIFIUTA_PROPOSTA, e MOTIVAZIONE",
            f"  2) {runner} review --run-id {run_id} --actor \"<il tuo nome>\"",
            "     (in alternativa aggiungi --interactive e rispondi dal terminale)",
        ]
    if current == 6:
        return [
            f"Review completata. Azioni simulate registrate: {len(state.get('action_receipts', []))} (nessun invio reale).",
            "",
            "PROSSIMO PASSO - annota in agent/EVIDENZE_PARTECIPANTE.md che cosa hai osservato.",
            "Fasi successive (challenge, report, consegna): vedi ESECUZIONE.md.",
        ]
    return [f"Stato non riconosciuto: {state['status']}."]


def render_run_map(value: dict[str, Any], open_runs: list[dict[str, Any]]) -> str:
    """Mappa del run: passi, attore, passo corrente e prossimo comando già compilato."""
    state = value["state"]
    tasks = value.get("approval_requests", {})
    mode = value.get("ai_execution_mode", "manual")
    roles = tasks.get("role_response_mode", "human") if tasks.get("enabled") else "disabilitate"
    session = f" (sessione operatore: {value.get('agent_session_status') or 'non preparata'})" if mode == "agent" else ""
    lines = [
        f"Run {state['run_id']}   workspace: {_shell_path(Path(value['workspace']))}",
        f"Stato del workflow: {state['status']}",
        f"Nodo AI: {mode}{session}   Risposte ai ruoli: {roles}",
        "",
    ]
    steps, current = _run_steps(value)
    for index, (title, who, where) in enumerate(steps):
        mark = "[x]" if index < current else "-->" if index == current else "[ ]"
        lines.append(f" {mark} {index + 1}. {title:<36} {who:<16} {where}")
    lines.append("")
    lines.extend(_next_step(value, current))
    others = [
        row for row in open_runs
        if row["run_id"] != state["run_id"] and row["status"] != "COMPLETED"
    ]
    if others:
        lines += ["", "ATTENZIONE: nel workspace ci sono altri run non completati. Indica sempre --run-id."]
        lines += [f"  {row['run_id']}  {row['status']}  (creato {row['created_at'][:16]})" for row in others]
    return "\n".join(lines)


def collect_interactive_decisions(
    lab: WorkflowLabService,
    run_id: str,
) -> Path:
    view = lab.resume(run_id)
    if view["state"]["status"] != "WAITING_FOR_APPROVAL":
        raise LabError(
            "invalid_state",
            "La review interattiva richiede lo stato WAITING_FOR_APPROVAL.",
        )
    print("Review interattiva. Valori ammessi: APPROVA_PROPOSTA, RIFIUTA_PROPOSTA.")
    blocks: list[str] = []
    for dataset_id in view["state"]["dataset_ids"]:
        proposal = view["decisions"][dataset_id]
        hard_stops = ", ".join(proposal.get("hard_stops", [])) or "nessuno"
        print(
            f"\n{dataset_id}: proposta {proposal['proposal']}; "
            f"hard stop: {hard_stops}"
        )
        decision = input("Decisione: ").strip().upper()
        reason = input("Motivazione: ").strip()
        blocks.append(
            f"""DATASET: {dataset_id}
DECISIONE: {decision}
MOTIVAZIONE:
{reason}"""
        )
    path = lab.store.exchange_path(run_id, "decisions.txt")
    atomic_write_text(path, "\n\n".join(blocks))
    return path


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    root.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable per test e debug; non necessario nel percorso normale.",
    )
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("check-agent-config")
    tasks = sub.add_parser("approval-requests")
    tasks.add_argument("--run-id", required=True)
    respond = sub.add_parser("respond-approval")
    respond.add_argument("--run-id", required=True)
    respond.add_argument("--task-id", required=True)
    respond.add_argument("--actor", required=True)
    respond.add_argument("--role", required=True)
    respond.add_argument("--decision", choices=["APPROVE", "REJECT"], required=True)
    respond.add_argument("--reason", required=True)
    respond.add_argument("--source", choices=["human", "model_simulated"], default="human")
    respond.add_argument("--model-label")
    prepare_agent = sub.add_parser("prepare-agent")
    prepare_agent.add_argument("--run-id", required=True)
    for name in ("fallback-agent", "stop-agent", "resume-agent", "reopen-agent"):
        transition = sub.add_parser(name)
        transition.add_argument("--run-id", required=True)
        transition.add_argument("--reason", required=True)
    freeze = sub.add_parser("freeze-spec")
    freeze.add_argument(
        "--docx",
        type=Path,
        default=BASE_DIR / "templates" / "workflow_spec_compilabile.docx",
    )
    freeze.add_argument(
        "--timestamp",
        help="Timestamp ISO opzionale per test deterministici.",
    )

    start = sub.add_parser("start")
    start.add_argument("--case", type=Path, default=DEFAULT_CASE)
    start.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    start.add_argument("--registry-backend", choices=("sqlite", "json"), default="sqlite")
    start.add_argument("--overlay", type=Path)
    start.add_argument("--roundtrip-index", type=int, choices=(1, 2), default=1)

    status = sub.add_parser("status")
    status.add_argument("--run-id")

    continue_run = sub.add_parser("continue")
    continue_run.add_argument("--run-id")
    continue_run.add_argument("--response", type=Path)

    review = sub.add_parser("review")
    review.add_argument("--run-id")
    review.add_argument("--actor", required=True)
    review.add_argument("--decisions", type=Path)
    review.add_argument(
        "--interactive",
        action="store_true",
        help="Acquisisce decisione e motivazione dal terminale.",
    )

    submit = sub.add_parser("submit")
    submit.add_argument("--run-id", action="append")
    submit.add_argument("--out", type=Path, default=Path("consegna.zip"))

    advanced_import = sub.add_parser("advanced-import-json")
    advanced_import.add_argument("--run-id")
    advanced_import.add_argument("--response", type=Path, required=True)

    advanced_approve = sub.add_parser("advanced-approve-json")
    advanced_approve.add_argument("--run-id")
    advanced_approve.add_argument("--actor", required=True)
    advanced_approve.add_argument("--reason", required=True)
    advanced_approve.add_argument("--decisions", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "check-agent-config":
            from meridiano_lab.agent_config import load_agent_config, render_agent_card
            config = load_agent_config(BASE_DIR, load_frozen_design(BASE_DIR))
            atomic_write_text(BASE_DIR / "build/agent/il_tuo_agente.md", render_agent_card(config))
            result = {"execution_mode": config["execution_mode"], "role_response_mode": config["role_response_mode"], "max_calls": config["max_calls"], "status": "VALID", "card": "build/agent/il_tuo_agente.md"}
            emit_json(result) if args.json else print(human_summary(args.command, result))
            return 0
        if args.command == "preflight":
            result = run_preflight(BASE_DIR)
        elif args.command == "freeze-spec":
            result = freeze_spec(
                BASE_DIR,
                args.docx,
                frozen_at=args.timestamp,
            )
        else:
            lab = service(args)
            if args.command in {"approval-requests", "respond-approval"}:
                from meridiano_lab.approval_tasks import ApprovalTasks
                with lab.store.run_lock(args.run_id):
                    lab._recover_import_locked(args.run_id)
                    tasks = ApprovalTasks(lab, args.run_id)
                    if args.command == "respond-approval":
                        tasks.respond(args.task_id, actor=args.actor, role=args.role, decision=args.decision, reason=args.reason,
                                      source=args.source, model_label=args.model_label)
                    result = lab.view(args.run_id)
            elif args.command == "prepare-agent":
                from meridiano_lab.agent_session import AgentSession
                result = AgentSession(lab, args.run_id).prepare()
            elif args.command in {"fallback-agent", "stop-agent", "resume-agent", "reopen-agent"}:
                from meridiano_lab.agent_session import AgentSession
                result = AgentSession(lab, args.run_id).transition(args.command.removesuffix("-agent"), args.reason)
            elif args.command == "start":
                result = lab.init_run(
                    args.case,
                    args.prompt,
                    registry_backend=args.registry_backend,
                    overlay_path=args.overlay,
                    roundtrip_index=args.roundtrip_index,
                )
            elif args.command == "status":
                result = lab.resume(resolve_run_id(lab, args.run_id))
            elif args.command == "continue":
                run_id = resolve_run_id(lab, args.run_id)
                response = args.response or lab.store.exchange_path(
                    run_id, "response.txt"
                )
                result = lab.import_response_text(run_id, response)
            elif args.command == "review":
                run_id = resolve_run_id(lab, args.run_id)
                if args.interactive and args.decisions:
                    raise LabError(
                        "conflicting_review_mode",
                        "Usa --interactive oppure --decisions, non entrambi.",
                    )
                decisions = (
                    collect_interactive_decisions(lab, run_id)
                    if args.interactive
                    else args.decisions
                    or lab.store.exchange_path(run_id, "decisions.txt")
                )
                result = lab.approve_text(
                    run_id,
                    actor=args.actor,
                    decisions_path=decisions,
                )
            elif args.command == "submit":
                run_ids = args.run_id or [
                    row["run_id"]
                    for row in lab.list_runs()
                    if row["status"] == "COMPLETED"
                ]
                result = (
                    lab.create_submission_archive(run_ids, args.out)
                    if args.out.suffix.casefold() == ".zip"
                    else lab.create_submission(run_ids, args.out)
                )
            elif args.command == "advanced-import-json":
                run_id = resolve_run_id(lab, args.run_id)
                result = lab.import_response_file(run_id, args.response)
            elif args.command == "advanced-approve-json":
                run_id = resolve_run_id(lab, args.run_id)
                result = lab.approve(
                    run_id,
                    actor=args.actor,
                    decisions=read_json(args.decisions),
                    reason=args.reason,
                )
            else:
                raise LabError("unknown_command", args.command)
        if args.json:
            emit_json(result)
        elif args.command == "prepare-agent":
            # Stessa mappa di status: il testo per l'operatore esce in un blocco delimitato.
            lines = ["Readiness verificata: sessione dell'operatore preparata.", ""]
            lines.append(render_run_map(lab.view(args.run_id), lab.list_runs()))
            if result.get("warning"):
                lines += ["", "ATTENZIONE: " + result["warning"]]
            print("\n".join(lines))
        else:
            open_runs = lab.list_runs() if "approval_requests" in result and "state" in result else []
            print(human_summary(args.command, result, open_runs))
        return 0
    except LabError as exc:
        if args.json:
            emit_json(exc.as_dict())
        else:
            print(f"Operazione non completata [{exc.code}]\n{exc.message}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
