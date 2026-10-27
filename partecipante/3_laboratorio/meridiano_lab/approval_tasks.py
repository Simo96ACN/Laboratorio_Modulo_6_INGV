"""Richieste e risposte di ruolo locali e simulate, distinte dalla review finale."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any

from .errors import LabError
from .text_exchange import render_decision_form
from .utils import atomic_write_json, atomic_write_text, path_is_file, read_json, sha256_value, utc_now, parse_timestamp

ROLES = {"publication_owner": "Publication Owner", "publication_steward": "Publication Steward"}


class ApprovalTasks:
    def __init__(self, service: Any, run_id: str):
        self.service = service
        self.store = service.store
        self.run_id = run_id
        self.path = self.store.artifact_path(run_id, "approval_tasks.json")

    def enabled(self) -> bool:
        return self.service.design["ai_delegation"]["approval_requests"] == "enabled"

    def response_mode(self) -> str:
        if self.service.participant_root:
            return read_json(self.service.participant_root / "workflow/agent_config.json").get("role_response_mode", "human")
        return "human"

    def load(self) -> dict[str, Any]:
        if path_is_file(self.path):
            ledger = read_json(self.path)
            if ledger.get("run_id") != self.run_id or ledger.get("design_sha256") != self.service.design["design_sha256"]:
                raise LabError("approval_task_correlation", "Richieste non correlate a run e spec.")
            return ledger
        return {"kind": "simulated_approval_tasks", "run_id": self.run_id,
                "design_sha256": self.service.design["design_sha256"], "tasks": [], "applied_responses": None}

    def _trace_once(self, event: str, task_id: str, **details: Any) -> None:
        if not any(row["event_type"] == event and row["details"].get("task_id") == task_id for row in self.store.trace(self.run_id)):
            self.store.append_trace(self.run_id, event, task_id=task_id, simulated=True, **details)

    def request(self, dataset: str, scope: str, reason: str, *, origin: str) -> dict[str, Any]:
        state = self.store.load_state(self.run_id)
        self.service._assert_design(state)
        if not self.enabled():
            raise LabError("approval_tasks_disabled", "Abilita le richieste simulate nella sezione 5 prima del freeze.")
        if state["status"] not in {"WAITING_FOR_AI", "WAITING_FOR_APPROVAL"}:
            raise LabError("approval_task_closed", "Il run non accetta nuove richieste.")
        if dataset not in state["dataset_ids"] or scope not in ROLES:
            raise LabError("approval_task_scope", "Dataset o ruolo estraneo al mandato.")
        if not isinstance(reason, str) or len(reason.strip()) < 10:
            raise LabError("approval_task_reason", "Motiva la richiesta con il fatto da confermare.")
        ledger = self.load()
        task_id = "TASK-" + sha256_value([self.run_id, dataset, scope])[:20]
        existing = next((row for row in ledger["tasks"] if row["task_id"] == task_id), None)
        if existing:
            return deepcopy(existing)
        normalized = read_json(self.store.artifact_path(self.run_id, "normalized_evidence.json"))
        version = normalized["by_dataset"][dataset]["registry"]["current_version"]
        if not version:
            raise LabError("approval_task_version", "Serve una versione attestata prima di chiedere una conferma.")
        task = {"task_id": task_id, "run_id": self.run_id, "dataset_id": dataset,
                "version": version["version"], "scope": scope, "target_role": ROLES[scope],
                "reason": reason.strip(), "origin": origin, "status": "PENDING",
                "created_at": utc_now(), "simulated": True, "response": None}
        ledger["tasks"].append(task)
        atomic_write_json(self.path, ledger)
        self._trace_once("simulated_approval_requested", task_id, dataset_id=dataset, scope=scope, origin=origin)
        return deepcopy(task)

    def from_policy(self, decisions: dict[str, Any]) -> None:
        if not self.enabled():
            return
        for dataset, decision in decisions.items():
            rows = decision.get("approval_requests")
            if not isinstance(rows, list):
                raise LabError("approval_plan_required", "Il TODO della policy deve restituire approval_requests quando la spec abilita le richieste.")
            for row in rows:
                if not isinstance(row, dict) or set(row) != {"scope", "reason"}:
                    raise LabError("approval_plan_contract", "Ogni richiesta della policy contiene scope e reason.")
                self.request(dataset, row["scope"], row["reason"], origin="workflow_policy")

    def view(self) -> dict[str, Any]:
        ledger = self.load()
        state = self.store.load_state(self.run_id)
        return {"enabled": self.enabled(), "roles": ROLES, "tasks": ledger["tasks"],
                "pending": sum(row["status"] == "PENDING" for row in ledger["tasks"]),
                "approval_gates": {dataset: gates.get("formal_approval") for dataset, gates in state["gates"].items()},
                "role_response_mode": self.response_mode(), "real_world_role": "human",
                "contains_model_simulated_responses": any(row["response"] and row["response"].get("source") == "model_simulated" for row in ledger["tasks"]),
                "is_real_approval": False, "simulated": True}

    def respond(self, task_id: str, *, actor: str, role: str, decision: str, reason: str,
                source: str = "human", model_label: str | None = None) -> dict[str, Any]:
        with self.store.run_lock(self.run_id):
            self.service._recover_import_locked(self.run_id)
            state = self.store.load_state(self.run_id)
            self.service._assert_design(state)
            if state["status"] not in {"WAITING_FOR_AI", "WAITING_FOR_APPROVAL"}:
                raise LabError("approval_task_closed", "Il run è chiuso.")
            ledger = self.load()
            task = next((row for row in ledger["tasks"] if row["task_id"] == task_id), None)
            if task is None or not self.enabled():
                raise LabError("approval_task_missing", "Richiesta assente o non abilitata.")
            if source not in {"human", "model_simulated"}:
                raise LabError("approval_response_source", "Dichiara human oppure model_simulated.")
            if source == "model_simulated":
                from .agent_config import load_agent_config
                if not self.service.participant_root or load_agent_config(self.service.participant_root, self.service.design)["role_response_mode"] != "model_simulated":
                    raise LabError("role_simulation_disabled", "La configurazione non abilita la risposta simulata dal modello.")
                if state["status"] != "WAITING_FOR_APPROVAL" or not isinstance(model_label, str) or not model_label.strip():
                    raise LabError("role_simulation_phase", "Prima importa la classificazione; indica poi il modello simulatore.")
                model_label = model_label.strip()
                actor = "Modello simulatore: " + model_label
            if role != task["target_role"] or decision not in {"APPROVE", "REJECT"} or not actor.strip() or len(reason.strip()) < 10:
                raise LabError("approval_task_response", "Servono ruolo destinatario, attore dichiarato, APPROVE/REJECT e motivazione.")
            response = {"actor": actor.strip(), "actor_role": role, "decision": decision, "reason": reason.strip(),
                        "source": source, "model_label": model_label if source == "model_simulated" else None,
                        "real_world_role": "human", "is_real_approval": False, "teaching_only": True}
            if task["response"]:
                legacy_defaults = {"source": "human", "model_label": None, "real_world_role": "human", "is_real_approval": False, "teaching_only": True}
                if any(task["response"].get(key, legacy_defaults.get(key)) != value for key, value in response.items()):
                    raise LabError("approval_task_replay_conflict", "La richiesta ha già una risposta diversa; non sovrascriverla.")
            else:
                task.update(status="RESPONDED", response={**response, "recorded_at": utc_now()})
                atomic_write_json(self.path, ledger)  # journal di autorità, prima della rivalutazione
            self.recover()
            return self.view()

    def recover(self) -> None:
        if not path_is_file(self.path):
            return
        ledger = self.load()
        for task in ledger["tasks"]:
            self._trace_once("simulated_approval_requested", task["task_id"], dataset_id=task["dataset_id"], scope=task["scope"], origin=task["origin"])
            if task["response"]:
                self._trace_once("simulated_role_responded", task["task_id"], decision=task["response"]["decision"], actor=task["response"]["actor"],
                                 response_source=task["response"].get("source", "human"), real_world_role="human", is_real_approval=False)
        responses = [row for row in ledger["tasks"] if row["response"]]
        state = self.store.load_state(self.run_id)
        fingerprint = sha256_value(responses)
        if state["status"] != "WAITING_FOR_APPROVAL" or not responses or ledger["applied_responses"] == fingerprint:
            return
        normalized = read_json(self.store.artifact_path(self.run_id, "normalized_evidence.json"))
        manifest = read_json(self.store.artifact_path(self.run_id, "case_manifest.json"))
        as_of = parse_timestamp(manifest["as_of"], "as_of")
        for index, task in enumerate(responses, 1):
            dataset = normalized["by_dataset"][task["dataset_id"]]
            version = dataset["registry"]["current_version"]
            if not version or version["version"] != task["version"]:
                raise LabError("approval_task_version", "Risposta riferita a una versione differente.")
            latest = max([as_of] + [parse_timestamp(row["decided_at"], "decided_at") for row in dataset["registry"]["approvals"]])
            timestamp = (latest + timedelta(microseconds=index)).isoformat()
            ref = "SIMULATED-" + task["task_id"]
            row = {"approval_event_id": ref, "object_id": task["dataset_id"], "scope": task["scope"],
                   "actor_role": task["target_role"], "decision": task["response"]["decision"],
                   "decided_at": timestamp, "evidence_ref": ref,
                   "response_source": task["response"].get("source", "human"), "teaching_only": True,
                   "real_world_role": "human", "is_real_approval": False}
            dataset["registry"]["approvals"].append(row)
            normalized["evidence"].append({"schema_version": "1.0", "kind": "normalized_evidence",
                "evidence_id": ref, "dataset_id": task["dataset_id"], "field": "approval." + task["scope"],
                "value": row, "source_id": "SIMULATED-MODEL-ROLE-RESPONSE" if row["response_source"] == "model_simulated" else "SIMULATED-ROLE-RESPONSE", "source_path": "approval_tasks.json",
                "source_record_id": task["task_id"], "observed_at": timestamp,
                "authority_scope": task["scope"], "freshness": "CURRENT", "status": "FACT",
                "raw_hash": sha256_value(task["response"]), "normalization_version": normalized["normalization_version"]})
        gates = self.service.implementation.evaluate_gates(deepcopy(normalized), deepcopy(manifest), deepcopy(self.service.design))
        self.service._validate_gates(gates, state["dataset_ids"])
        original = read_json(self.store.artifact_path(self.run_id, "deterministic_gates.json"))
        for dataset, dataset_gates in original.items():
            if {key: value for key, value in dataset_gates.items() if key != "formal_approval"} != {key: value for key, value in gates[dataset].items() if key != "formal_approval"}:
                raise LabError("approval_task_scope", "Una risposta di pubblicazione non può cambiare qualità, diritti o altri gate.")
        ai_results = read_json(self.store.artifact_path(self.run_id, "ai_results.json"))
        decisions = self.service.implementation.decide(deepcopy(gates), deepcopy(ai_results), deepcopy(normalized), deepcopy(self.service.design))
        self.service._validate_decisions(decisions, state["dataset_ids"])
        atomic_write_json(self.store.artifact_path(self.run_id, "approval_reassessment.json"), {
            "kind": "simulated_role_reassessment", "run_id": self.run_id, "responses_sha256": fingerprint,
            "normalized": normalized, "gates": gates, "decisions": decisions, "simulated": True,
            "contains_model_simulated_responses": any(row["response"].get("source") == "model_simulated" for row in responses),
            "real_world_role": "human", "is_real_approval": False})
        atomic_write_json(self.store.artifact_path(self.run_id, "decisions.json"), decisions)
        atomic_write_text(self.store.exchange_path(self.run_id, "decisions.txt"), render_decision_form(decisions))
        state.update(gates=gates, decisions=decisions, updated_at=utc_now())
        state["artifacts"]["approval_reassessment"] = "approval_reassessment.json"
        self.store.save_state(state)
        for task in responses:
            self._trace_once("simulated_gates_reassessed", task["task_id"], responses_sha256=fingerprint)
        ledger["applied_responses"] = fingerprint
        atomic_write_json(self.path, ledger)
