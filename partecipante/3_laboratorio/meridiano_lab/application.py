from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .errors import LabError
from .protocols import WorkflowImplementation
from .readers import load_case
from .store import RunStore, atomic_write_bytes
from .text_exchange import (
    parse_ai_response,
    parse_decisions,
    render_decision_form,
    render_prompt,
    render_response_form,
)
from .utils import (
    SCHEMA_VERSION,
    atomic_write_json,
    atomic_write_text,
    identifier,
    make_dirs,
    os_fspath,
    parse_timestamp,
    path_exists,
    path_is_file,
    read_bytes,
    read_json,
    read_text,
    require_keys,
    sha256_file,
    sha256_value,
    utc_now,
    walk_files,
)
from .workflow_design import choice_summary, validate_workflow_design


STATUS_NEW = "NEW"
STATUS_DATA_READY = "DATA_READY"
STATUS_WAITING_FOR_AI = "WAITING_FOR_AI"
STATUS_WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
STATUS_COMPLETED = "COMPLETED"
NODE_ID = "classify_evidence"
AI_LABELS = {"SAFE", "SENSITIVE", "UNKNOWN"}


class WorkflowLabService:
    """Application service condiviso da runner, reference ed evaluator."""

    def __init__(
        self,
        workspace: Path,
        implementation: WorkflowImplementation,
        design: dict[str, Any],
        *,
        participant_root: Path | None = None,
    ):
        validate_workflow_design(design)
        self.store = RunStore(workspace)
        self.implementation = implementation
        self.design = deepcopy(design)
        self.participant_root = (
            participant_root.resolve() if participant_root else None
        )

    def _assert_design(self, state: dict[str, Any]) -> None:
        if (
            state.get("spec_id") != self.design["spec_id"]
            or state.get("workflow_design_sha256")
            != self.design["design_sha256"]
        ):
            raise LabError(
                "run_design_mismatch",
                "Il run è stato creato con una spec diversa. "
                "Ripristina il design originale o avvia un nuovo run.",
            )

    def init_run(
        self,
        case_root: Path,
        prompt_path: Path,
        *,
        registry_backend: str = "sqlite",
        overlay_path: Path | None = None,
        roundtrip_index: int = 1,
        prompt_version: str = "1.0",
    ) -> dict[str, Any]:
        config = {}
        if self.participant_root:
            from .agent_config import load_agent_config
            config = load_agent_config(self.participant_root, self.design)
        if roundtrip_index not in {1, 2}:
            raise LabError("roundtrip_budget", "roundtrip_index deve essere 1 oppure 2.")
        prompt_template = prompt_path.read_text(encoding="utf-8").strip()
        if (
            not prompt_template
            or "TODO_PARTECIPANTE" in prompt_template
            or "[TODO" in prompt_template
        ):
            raise LabError(
                "todo_incomplete",
                "Completare workflow/prompts/classify_evidence.txt prima del run.",
            )
        if "{{EVIDENCE}}" not in prompt_template:
            raise LabError(
                "invalid_prompt_contract",
                "Il prompt deve contenere il placeholder {{EVIDENCE}}.",
            )

        manifest, loaded = load_case(
            case_root,
            registry_backend=registry_backend,
            overlay_path=overlay_path,
        )
        run_id = identifier("RUN")
        self.store.create(run_id)
        now = utc_now()
        state: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "kind": "run_state",
            "run_id": run_id,
            "case_id": manifest["case_id"],
            "scenario_version": manifest["scenario_version"],
            "implementation_id": self.implementation.implementation_id,
            "spec_id": self.design["spec_id"],
            "workflow_design_sha256": self.design["design_sha256"],
            "source_docx_sha256": self.design["source_docx_sha256"],
            "status": STATUS_NEW,
            "dataset_ids": manifest["dataset_ids"],
            "roundtrip_index": roundtrip_index,
            "registry_backend": registry_backend,
            "overlay": loaded["inventory"]["overlay"],
            "created_at": now,
            "updated_at": now,
            "active_request_id": None,
            "accepted_response_id": None,
            "approval_id": None,
            "artifacts": {},
            "gates": {},
            "decisions": {},
            "action_receipts": [],
            "outcome": None,
        }
        self.store.save_state(state)
        self.store.append_trace(
            run_id,
            "workflow_design_loaded",
            spec_id=self.design["spec_id"],
            design_sha256=self.design["design_sha256"],
            source_docx_sha256=self.design["source_docx_sha256"],
            choices=choice_summary(self.design),
        )
        if self.design["interaction_policy"]["trace_level"] == "extended":
            self.store.append_trace(
                run_id,
                "workflow_design_details",
                policy_choices=self.design["policy_choices"],
                interaction_policy={
                    key: value
                    for key, value in self.design[
                        "interaction_policy"
                    ].items()
                    if key != "touchpoints"
                },
                selected_dimensions=self.design["selected_dimensions"],
            )
        self.store.append_trace(
            run_id,
            "run_created",
            case_id=manifest["case_id"],
            scenario_version=manifest["scenario_version"],
            implementation_id=self.implementation.implementation_id,
            registry_backend=registry_backend,
            overlay=loaded["inventory"]["overlay"],
        )

        inventory_path = self.store.artifact_path(run_id, "raw_inventory.json")
        atomic_write_json(inventory_path, loaded["inventory"])
        atomic_write_json(self.store.artifact_path(run_id, "case_manifest.json"), manifest)
        self.store.append_trace(
            run_id,
            "raw_sources_loaded",
            counts=loaded["inventory"]["counts"],
            registry_counts=loaded["inventory"]["registry_counts"],
        )

        normalized = self.implementation.normalize(
            loaded["bundle"],
            manifest,
            self.design,
        )
        self._validate_normalized(normalized, manifest)
        normalized_path = self.store.artifact_path(
            run_id, "normalized_evidence.json"
        )
        atomic_write_json(normalized_path, normalized)
        self.store.append_trace(
            run_id,
            "normalization_completed",
            normalization_version=normalized["normalization_version"],
            stats=normalized["stats"],
        )

        gates = self.implementation.evaluate_gates(
            normalized,
            manifest,
            self.design,
        )
        self._validate_gates(gates, manifest["dataset_ids"])
        gates_path = self.store.artifact_path(run_id, "deterministic_gates.json")
        atomic_write_json(gates_path, gates)
        state["status"] = STATUS_DATA_READY
        state["gates"] = gates
        state["artifacts"].update(
            {
                "raw_inventory": inventory_path.name,
                "normalized_evidence": normalized_path.name,
                "deterministic_gates": gates_path.name,
            }
        )
        state["updated_at"] = utc_now()
        self.store.save_state(state)
        self.store.append_trace(
            run_id,
            "state_transition",
            from_status=STATUS_NEW,
            to_status=STATUS_DATA_READY,
        )

        evidence_by_dataset = {
            dataset_id: [
                {
                    "evidence_ref": item["evidence_ref"],
                    "source_path": item["source_path"],
                    "text": item["text"],
                    "observed_at": item["observed_at"],
                }
                for item in normalized["by_dataset"][dataset_id]["texts"]
            ]
            for dataset_id in manifest["dataset_ids"]
        }
        if any(not rows for rows in evidence_by_dataset.values()):
            raise LabError(
                "missing_ai_evidence",
                "Ogni dataset deve avere almeno una evidenza testuale.",
            )
        payload = {
            "evidence_by_dataset": evidence_by_dataset,
            "workflow_context": {
                "spec_id": self.design["spec_id"],
                "design_sha256": self.design["design_sha256"],
                "ai_decisions": self.design["ai_delegation"][
                    "ai_decisions"
                ],
                "ai_may_approve": False,
                "approval_requests": self.design["ai_delegation"]["approval_requests"],
                "role_response_mode": config.get("role_response_mode", "human"),
                "ai_validation": self.design["interaction_policy"][
                    "ai_validation"
                ],
                "minimum_independent_evidence": self.design[
                    "policy_choices"
                ]["minimum_independent_evidence"],
            },
        }
        rendered_prompt = prompt_template.replace(
            "{{EVIDENCE}}",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        )
        request_id = identifier("REQ")
        request = {
            "schema_version": SCHEMA_VERSION,
            "kind": "ai_request",
            "request_id": request_id,
            "run_id": run_id,
            "case_id": manifest["case_id"],
            "scenario_version": manifest["scenario_version"],
            "node_id": NODE_ID,
            "dataset_ids": manifest["dataset_ids"],
            "roundtrip_index": roundtrip_index,
            "created_at": utc_now(),
            "prompt_version": prompt_version,
            "prompt_template": prompt_template,
            "prompt_snapshot_version": "1.0",
            "prompt_hash": sha256_value(
                {
                    "prompt_template": prompt_template,
                    "prompt_version": prompt_version,
                }
            ),
            "payload_hash": sha256_value(payload),
            "prompt_text": rendered_prompt,
            "payload": payload,
            "response_contract": {
                "labels": ["SAFE", "SENSITIVE", "UNKNOWN"],
                "required_fields": [
                    "dataset_id",
                    "label",
                    "evidence_refs",
                    "rationale",
                    "uncertainties",
                ],
                "coverage": "exactly_one_output_per_requested_dataset",
                "minimum_independent_evidence": self.design[
                    "policy_choices"
                ]["minimum_independent_evidence"],
                "validation_mode": self.design["interaction_policy"][
                    "ai_validation"
                ],
                "may_approve": False,
            },
        }
        request_path = self.store.request_path(run_id, request_id)
        atomic_write_json(request_path, request)
        human_prompt_path = self.store.exchange_path(run_id, "prompt.txt")
        response_form_path = self.store.exchange_path(run_id, "response.txt")
        atomic_write_text(
            human_prompt_path,
            render_prompt(prompt_template, request),
        )
        atomic_write_text(
            response_form_path,
            render_response_form(manifest["dataset_ids"]),
        )
        state["active_request_id"] = request_id
        state["artifacts"]["active_request"] = (
            f"ai_requests/{request_path.name}"
        )
        state["artifacts"]["human_prompt"] = "exchange/prompt.txt"
        state["artifacts"]["human_response"] = "exchange/response.txt"
        previous = state["status"]
        state["status"] = STATUS_WAITING_FOR_AI
        state["updated_at"] = utc_now()
        self.store.save_state(state)
        self.store.append_trace(
            run_id,
            "ai_request_exported",
            request_id=request_id,
            node_id=NODE_ID,
            prompt_hash=request["prompt_hash"],
            payload_hash=request["payload_hash"],
            roundtrip_index=roundtrip_index,
            human_prompt_sha256=sha256_file(human_prompt_path),
        )
        self.store.append_trace(
            run_id,
            "state_transition",
            from_status=previous,
            to_status=STATUS_WAITING_FOR_AI,
        )
        return self.view(run_id)

    def _validate_normalized(
        self,
        normalized: dict[str, Any],
        manifest: dict[str, Any],
    ) -> None:
        if normalized.get("kind") != "normalized_bundle":
            raise LabError("invalid_normalized_bundle", "kind non valido.")
        expected = set(manifest["dataset_ids"])
        if set(normalized.get("dataset_ids", [])) != expected:
            raise LabError(
                "normalization_coverage",
                "La normalizzazione non copre tutti i dataset.",
            )
        if set(normalized.get("by_dataset", {})) != expected:
            raise LabError(
                "normalization_coverage",
                "by_dataset non copre tutti i dataset.",
            )
        evidence = normalized.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise LabError("missing_evidence", "Nessuna evidenza normalizzata.")
        ids: list[str] = []
        required = {
            "schema_version",
            "kind",
            "evidence_id",
            "dataset_id",
            "field",
            "value",
            "source_id",
            "source_path",
            "source_record_id",
            "observed_at",
            "authority_scope",
            "freshness",
            "status",
            "raw_hash",
            "normalization_version",
        }
        for record in evidence:
            if not isinstance(record, dict) or not required.issubset(record):
                raise LabError(
                    "invalid_normalized_evidence",
                    "Record normalizzato incompleto.",
                )
            if record["dataset_id"] not in expected:
                raise LabError("foreign_evidence_dataset", record["dataset_id"])
            parse_timestamp(record["observed_at"], "observed_at")
            ids.append(record["evidence_id"])
        if len(ids) != len(set(ids)):
            raise LabError("duplicate_evidence", "evidence_id duplicato.")

    def _validate_gates(
        self,
        gates: dict[str, Any],
        dataset_ids: list[str],
    ) -> None:
        if set(gates) != set(dataset_ids):
            raise LabError("gate_coverage", "Gate incompleti.")
        allowed = {"PASS", "FAIL", "UNKNOWN", "CONFLICT"}
        for dataset_id, dataset_gates in gates.items():
            if not isinstance(dataset_gates, dict) or not dataset_gates:
                raise LabError("invalid_gates", dataset_id)
            for name, gate in dataset_gates.items():
                if gate.get("result") not in allowed:
                    raise LabError(
                        "invalid_gate_result",
                        f"{dataset_id}/{name}: {gate.get('result')}",
                    )

    def _active_request(self, state: dict[str, Any]) -> dict[str, Any]:
        request_id = state.get("active_request_id")
        if not request_id:
            raise LabError("corrupt_state", "active_request_id mancante.")
        request = read_json(self.store.request_path(state["run_id"], request_id))
        if (
            request.get("run_id") != state["run_id"]
            or request.get("case_id") != state["case_id"]
        ):
            raise LabError("corrupt_request", "Request non correlata allo stato.")
        return request

    def response_template(self, run_id: str) -> dict[str, Any]:
        state = self.store.load_state(run_id)
        self._assert_design(state)
        if state["status"] != STATUS_WAITING_FOR_AI:
            raise LabError(
                "invalid_state",
                "Il template è disponibile soltanto in WAITING_FOR_AI.",
            )
        request = self._active_request(state)
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "ai_response",
            "response_id": identifier("RESP"),
            "run_id": run_id,
            "request_id": request["request_id"],
            "node_id": request["node_id"],
            "prompt_hash": request["prompt_hash"],
            "payload_hash": request["payload_hash"],
            "created_at": utc_now(),
            "outputs": [
                {
                    "dataset_id": dataset_id,
                    "label": "TODO",
                    "evidence_refs": [
                        row["evidence_ref"]
                        for row in request["payload"]["evidence_by_dataset"][
                            dataset_id
                        ]
                    ],
                    "rationale": "TODO_PARTECIPANTE",
                    "uncertainties": [],
                }
                for dataset_id in request["dataset_ids"]
            ],
        }

    def _validate_ai_response_structure(
        self,
        response: dict[str, Any],
    ) -> None:
        if not isinstance(response, dict):
            raise LabError("contract_violation", "AIResponse deve essere un oggetto.")
        required = {
            "schema_version",
            "kind",
            "response_id",
            "run_id",
            "request_id",
            "node_id",
            "prompt_hash",
            "payload_hash",
            "created_at",
            "outputs",
        }
        require_keys(response, required, required, "AIResponse")
        if any(not isinstance(response[field], str) for field in required - {"outputs"}):
            raise LabError("contract_violation", "Gli header AIResponse devono essere stringhe.")
        if (
            response["schema_version"] != SCHEMA_VERSION
            or response["kind"] != "ai_response"
        ):
            raise LabError("contract_violation", "Header AIResponse non valido.")
        for field in ("response_id", "run_id", "request_id", "node_id"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", str(response[field])):
                raise LabError(
                    "contract_violation",
                    f"{field} contiene caratteri non ammessi.",
                )
        if any(not re.fullmatch(r"[a-f0-9]{64}", response[field]) for field in ("prompt_hash", "payload_hash")):
            raise LabError("contract_violation", "Hash AIResponse non valido.")
        if not isinstance(response["outputs"], list):
            raise LabError("contract_violation", "outputs deve essere una lista.")
        output_fields = {
            "dataset_id",
            "label",
            "evidence_refs",
            "rationale",
            "uncertainties",
        }
        for row in response["outputs"]:
            if not isinstance(row, dict):
                raise LabError("contract_violation", "Output non oggetto.")
            require_keys(row, output_fields, output_fields, "AIResponse.outputs")
            if (
                not isinstance(row["dataset_id"], str)
                or not row["dataset_id"].strip()
                or not isinstance(row["label"], str)
                or not isinstance(row["rationale"], str)
                or not isinstance(row["evidence_refs"], list)
                or any(not isinstance(value, str) for value in row["evidence_refs"])
                or not isinstance(row["uncertainties"], list)
                or any(not isinstance(value, str) for value in row["uncertainties"])
            ):
                raise LabError("contract_violation", "Tipi dei campi output AI non validi.")
            if row["label"] not in AI_LABELS:
                raise LabError("contract_violation", f"Label non valida: {row['label']}")
            if (
                not isinstance(row["evidence_refs"], list)
                or len(row["evidence_refs"]) != len(set(row["evidence_refs"]))
                or not isinstance(row["uncertainties"], list)
                or not str(row["rationale"]).strip()
            ):
                raise LabError("contract_violation", "Campi output AI non validi.")
        if parse_timestamp(response["created_at"], "AIResponse.created_at").tzinfo is None:
            raise LabError("invalid_timestamp", "AIResponse.created_at deve includere il fuso orario.")

    def validate_response(
        self,
        run_id: str,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Controlli comuni senza import, decide, trace o modifiche di stato.

        L'hook del partecipante riceve copie indipendenti. Il suo contratto vieta
        I/O: queste copie difendono gli input, non isolano codice Python ostile.
        """
        with self.store.run_lock(run_id):
            state = self.store.load_state(run_id)
            self._assert_design(state)
            if state["status"] != STATUS_WAITING_FOR_AI:
                raise LabError("invalid_state", f"Validazione non ammessa in {state['status']}.")
            request = self._active_request(state)
            self._validate_ai_response_structure(response)
            correlations = {
                "run_id": run_id,
                "request_id": request["request_id"],
                "node_id": request["node_id"],
                "prompt_hash": request["prompt_hash"],
                "payload_hash": request["payload_hash"],
            }
            for field, expected in correlations.items():
                if response[field] != expected:
                    raise LabError("response_correlation_mismatch", f"{field} non corrisponde alla richiesta attiva.")
            if parse_timestamp(response["created_at"], "AIResponse.created_at") < parse_timestamp(request["created_at"], "AIRequest.created_at"):
                raise LabError("stale_response", "La risposta precede la richiesta attiva.")
            normalized = read_json(self.store.artifact_path(run_id, "normalized_evidence.json"))
            return deepcopy(self.implementation.validate_ai_outputs(
                deepcopy(request), deepcopy(response), deepcopy(normalized), deepcopy(self.design)
            ))

    def _journal_path(self, run_id: str) -> Path:
        return self.store.artifact_path(run_id, "import_transaction.json")

    def _prepare_import_result(self, run_id: str, journal: dict[str, Any]) -> None:
        # Il journal PREPARED precede l'elaborazione di policy. Dopo READY il
        # recupero ripubblica soltanto lo stesso risultato, senza richiamare decide.
        state = deepcopy(journal["initial_state"])
        self._assert_design(state)
        normalized = read_json(self.store.artifact_path(run_id, "normalized_evidence.json"))
        decisions = self.implementation.decide(
            deepcopy(state["gates"]), deepcopy(journal["ai_results"]),
            deepcopy(normalized), deepcopy(self.design),
        )
        self._validate_decisions(decisions, state["dataset_ids"])
        response = journal["response"]
        state["accepted_response_id"] = response["response_id"]
        state["decisions"] = decisions
        state["artifacts"].update({
            "accepted_response": f"ai_responses/{response['response_id']}.json",
            "ai_results": "ai_results.json",
            "decisions": "decisions.json",
            "human_decisions": "exchange/decisions.txt",
        })
        state["status"] = STATUS_WAITING_FOR_APPROVAL
        state["updated_at"] = utc_now()
        state["import_transaction_id"] = journal["transaction_id"]
        journal.update(phase="READY", decisions=decisions, final_state=state)
        atomic_write_json(self._journal_path(run_id), journal)

    def _recover_import_locked(self, run_id: str) -> str | None:
        path = self._journal_path(run_id)
        if not path_exists(path):
            from .approval_tasks import ApprovalTasks
            ApprovalTasks(self, run_id).recover()
            return None
        journal = read_json(path)
        if journal.get("run_id") != run_id or journal.get("kind") != "response_import_transaction":
            raise LabError("corrupt_import_journal", "Journal non correlato al run.")
        if journal.get("phase") in {"COMMITTED", "REJECTED"}:
            from .approval_tasks import ApprovalTasks
            ApprovalTasks(self, run_id).recover()
            return None
        transaction_id = journal["transaction_id"]
        state = self.store.load_state(run_id)
        self._assert_design(state)
        if state.get("import_transaction_id") not in {None, transaction_id}:
            raise LabError("corrupt_import_journal", "Un'altra transazione è già stata importata.")
        from .agent_session import AgentSession
        session = AgentSession(self, run_id)
        if journal["phase"] == "PREPARED":
            if state["status"] != STATUS_WAITING_FOR_AI:
                raise LabError("corrupt_import_journal", "Stato incompatibile con PREPARED.")
            session.recover()
            text = journal.get("source_text")
            session.verify_import(journal["response"], text_bytes=text.encode("utf-8") if text is not None else None)
            self._prepare_import_result(run_id, journal)
        if journal["phase"] != "READY":
            raise LabError("corrupt_import_journal", "Fase sconosciuta.")
        response = journal["response"]
        if journal.get("source_text") is not None:
            atomic_write_bytes(self.store.exchange_path(run_id, "response.txt"), journal["source_text"].encode("utf-8"))
        atomic_write_json(self.store.response_path(run_id, response["response_id"]), response)
        atomic_write_json(self.store.artifact_path(run_id, "ai_results.json"), journal["ai_results"])
        atomic_write_json(self.store.artifact_path(run_id, "decisions.json"), journal["decisions"])
        atomic_write_text(self.store.exchange_path(run_id, "decisions.txt"), render_decision_form(journal["decisions"]))
        if state.get("import_transaction_id") != transaction_id:
            self.store.save_state(journal["final_state"])
        events = []
        if journal.get("source_text") is not None:
            events.append(("human_text_response_parsed", {
                "source_sha256": sha256_value(journal["source_text"].encode("utf-8")),
                "derived_response_id": response["response_id"],
            }))
        events.extend([
            ("ai_response_accepted", {"response_id": response["response_id"], "request_id": response["request_id"]}),
            ("decisions_proposed", {"proposals": {key: value["proposal"] for key, value in journal["decisions"].items()}}),
            ("state_transition", {"from_status": STATUS_WAITING_FOR_AI, "to_status": STATUS_WAITING_FOR_APPROVAL}),
        ])
        for event_type, details in events:
            if not any(event["event_type"] == event_type and event["details"].get("transaction_id") == transaction_id for event in self.store.trace(run_id)):
                self.store.append_trace(run_id, event_type, transaction_id=transaction_id, **details)
        session.close_import(transaction_id)
        from .approval_tasks import ApprovalTasks
        tasks = ApprovalTasks(self, run_id)
        tasks.from_policy(journal["decisions"])
        tasks.recover()
        journal["phase"] = "COMMITTED"
        atomic_write_json(path, journal)
        return transaction_id

    def recover_import(self, run_id: str) -> str | None:
        """Completa la transazione pubblicata prima di consentire altre mutazioni."""
        with self.store.run_lock(run_id):
            return self._recover_import_locked(run_id)

    def _import_response_locked(
        self, run_id: str, response: dict[str, Any], *, source_text: bytes | None = None,
    ) -> dict[str, Any]:
        self._recover_import_locked(run_id)
        state = self.store.load_state(run_id)
        self._assert_design(state)
        if not isinstance(response, dict):
            raise LabError("contract_violation", "AIResponse deve essere un oggetto.")
        response_id = str(response.get("response_id", ""))
        if state["status"] != STATUS_WAITING_FOR_AI:
            if response_id == state.get("accepted_response_id"):
                raise LabError("duplicate_response", response_id)
            raise LabError("invalid_state", f"Import non ammesso in {state['status']}.")
        try:
            ai_results = self.validate_response(run_id, response)
            if path_exists(self.store.response_path(run_id, response_id)):
                raise LabError("duplicate_response", response_id)
            from .agent_session import AgentSession
            session = AgentSession(self, run_id)
            session.recover()
            receipt = session.verify_import(response, text_bytes=source_text)
            journal = {
                "schema_version": SCHEMA_VERSION,
                "kind": "response_import_transaction",
                "transaction_id": identifier("IMP"),
                "run_id": run_id,
                "phase": "PREPARED",
                "receipt": receipt,
                "response": deepcopy(response),
                "source_text": source_text.decode("utf-8") if source_text is not None else None,
                "ai_results": deepcopy(ai_results),
                "initial_state": deepcopy(state),
            }
            atomic_write_json(self._journal_path(run_id), journal)
            self._prepare_import_result(run_id, journal)
        except LabError as exc:
            path = self._journal_path(run_id)
            if path_exists(path):
                previous_journal = read_json(path)
                if previous_journal.get("phase") == "PREPARED":
                    previous_journal["phase"] = "REJECTED"
                    atomic_write_json(path, previous_journal)
            self.store.append_trace(run_id, "ai_response_rejected", code=exc.code,
                                    message=exc.message, response_id=response_id or None)
            raise
        self._recover_import_locked(run_id)
        return self.view(run_id)

    def import_response(self, run_id: str, response: dict[str, Any]) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            return self._import_response_locked(run_id, deepcopy(response))

    def import_response_text(self, run_id: str, response_path: Path) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            self._recover_import_locked(run_id)
            state = self.store.load_state(run_id)
            self._assert_design(state)
            if state["status"] != STATUS_WAITING_FOR_AI:
                raise LabError("invalid_state", f"Import testuale non ammesso in {state['status']}.")
            from .agent_session import AgentSession
            session = AgentSession(self, run_id)
            session.recover()
            source = response_path.resolve()
            try:
                text_bytes = read_bytes(source)
                session.verify_text_source(text_bytes)
                text = text_bytes.decode("utf-8")
            except FileNotFoundError as exc:
                raise LabError("missing_response_text", str(source)) from exc
            except UnicodeDecodeError as exc:
                raise LabError("invalid_text_response", "La risposta deve essere UTF-8.") from exc
            response = parse_ai_response(text, self._active_request(state))
            # Nessuna copia nel canonico fino al controllo della ricevuta.
            return self._import_response_locked(run_id, response, source_text=text_bytes)

    def import_response_file(self, run_id: str, response_path: Path) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            return self._import_response_locked(run_id, read_json(response_path.resolve()))

    def approve_text(
        self,
        run_id: str,
        *,
        actor: str,
        decisions_path: Path,
    ) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            self._recover_import_locked(run_id)
            return self._approve_text_locked(run_id, actor=actor, decisions_path=decisions_path)

    def _approve_text_locked(
        self,
        run_id: str,
        *,
        actor: str,
        decisions_path: Path,
    ) -> dict[str, Any]:
        state = self.store.load_state(run_id)
        self._assert_design(state)
        if state["status"] != STATUS_WAITING_FOR_APPROVAL:
            raise LabError(
                "invalid_state",
                f"Review testuale non ammessa in {state['status']}.",
            )
        source = decisions_path.resolve()
        try:
            text = read_text(source)
        except FileNotFoundError as exc:
            raise LabError("missing_decision_text", str(source)) from exc
        records = parse_decisions(text, state["dataset_ids"])
        canonical_path = self.store.exchange_path(run_id, "decisions.txt")
        atomic_write_text(canonical_path, text)
        records_path = self.store.artifact_path(
            run_id, "human_decision_records.json"
        )
        atomic_write_json(
            records_path,
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "human_decision_records",
                "run_id": run_id,
                "actor": actor.strip(),
                "records": records,
                "source_sha256": sha256_file(canonical_path),
            },
        )
        decisions = {
            record["dataset_id"]: record["decision"] for record in records
        }
        aggregate_reason = " | ".join(
            f"{record['dataset_id']}: {record['reason']}" for record in records
        )
        view = self.approve(
            run_id,
            actor=actor,
            decisions=decisions,
            reason=aggregate_reason,
        )
        completed = self.store.load_state(run_id)
        completed["artifacts"]["human_decision_records"] = records_path.name
        completed["artifacts"]["human_decisions"] = "exchange/decisions.txt"
        self.store.save_state(completed)
        self.store.append_trace(
            run_id,
            "human_text_decisions_parsed",
            records=len(records),
            source_sha256=sha256_file(canonical_path),
        )
        return self.view(run_id)

    def _validate_decisions(
        self,
        decisions: dict[str, Any],
        dataset_ids: list[str],
    ) -> None:
        if set(decisions) != set(dataset_ids):
            raise LabError("decision_coverage", "Decisioni incomplete.")
        allowed = {
            "PUBBLICA",
            "PUBBLICA_CON_CONDIZIONI",
            "TRATTIENI",
            "ESCALA",
        }
        for dataset_id, decision in decisions.items():
            if self.design["ai_delegation"]["approval_requests"] == "enabled":
                requests = decision.get("approval_requests")
                if not isinstance(requests, list):
                    raise LabError("approval_plan_required", "La policy deve dichiarare approval_requests, anche come lista vuota.")
                for row in requests:
                    if not isinstance(row, dict) or set(row) != {"scope", "reason"} or row["scope"] not in {"publication_owner", "publication_steward"} or not isinstance(row["reason"], str) or len(row["reason"].strip()) < 10:
                        raise LabError("approval_plan_contract", "Richiesta di ruolo non valida.")
            if (
                decision.get("dataset_id") != dataset_id
                or decision.get("proposal") not in allowed
                or not isinstance(decision.get("hard_stop"), bool)
            ):
                raise LabError("invalid_decision", dataset_id)

    def approve(
        self,
        run_id: str,
        *,
        actor: str,
        decisions: dict[str, str],
        reason: str,
    ) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            self._recover_import_locked(run_id)
            return self._approve_locked(run_id, actor=actor, decisions=decisions, reason=reason)

    def _approve_locked(
        self,
        run_id: str,
        *,
        actor: str,
        decisions: dict[str, str],
        reason: str,
    ) -> dict[str, Any]:
        state = self.store.load_state(run_id)
        self._assert_design(state)
        if state["status"] == STATUS_COMPLETED:
            existing = read_json(
                self.store.approval_path(run_id, state["approval_id"])
            )
            if existing["actor"] == actor and existing["decisions"] == decisions:
                self.store.append_trace(
                    run_id,
                    "approval_replay_deduplicated",
                    approval_id=existing["approval_id"],
                    action_receipts=state["action_receipts"],
                )
                return self.view(run_id)
            raise LabError(
                "invalid_state",
                "Run già completato con una approval diversa.",
            )
        if state["status"] != STATUS_WAITING_FOR_APPROVAL:
            raise LabError(
                "invalid_state",
                f"Approval non ammessa in {state['status']}.",
            )
        from .approval_tasks import ApprovalTasks
        if ApprovalTasks(self, run_id).view()["pending"]:
            raise LabError("pending_role_responses", "Raccogli le risposte simulate dei ruoli prima della review finale.")
        if not actor.strip() or len(reason.strip()) < 3:
            raise LabError("invalid_approval", "Attore e motivazione obbligatori.")
        if set(decisions) != set(state["dataset_ids"]):
            raise LabError(
                "approval_coverage",
                "Serve una decisione umana per ogni dataset.",
            )
        allowed = {"APPROVE_PROPOSAL", "REJECT_PROPOSAL"}
        if any(value not in allowed for value in decisions.values()):
            raise LabError("invalid_approval", "Decisione approval non valida.")

        approval = {
            "schema_version": SCHEMA_VERSION,
            "kind": "run_approval",
            "approval_id": identifier("APR"),
            "run_id": run_id,
            "actor": actor.strip(),
            "scope": "simulated_release_batch",
            "decisions": decisions,
            "reason": reason.strip(),
            "decided_at": utc_now(),
        }
        approval_path = self.store.approval_path(
            run_id, approval["approval_id"]
        )
        atomic_write_json(approval_path, approval)
        self.store.append_trace(
            run_id,
            "run_approval_recorded",
            approval_id=approval["approval_id"],
            actor=approval["actor"],
            decisions=decisions,
        )

        receipts: list[str] = []
        for dataset_id in state["dataset_ids"]:
            proposal = state["decisions"][dataset_id]
            approved = decisions[dataset_id] == "APPROVE_PROPOSAL"
            can_act = (
                approved
                and proposal["proposal"]
                in {"PUBBLICA", "PUBBLICA_CON_CONDIZIONI"}
                and proposal["hard_stop"] is False
            )
            if can_act:
                receipt = self._simulate_action(
                    run_id, dataset_id, proposal["proposal"]
                )
                receipts.append(
                    f"actions/{self.store.action_path(run_id, receipt['idempotency_key']).name}"
                )
            else:
                self.store.append_trace(
                    run_id,
                    "dataset_held",
                    dataset_id=dataset_id,
                    proposal=proposal["proposal"],
                    human_decision=decisions[dataset_id],
                    hard_stop=proposal["hard_stop"],
                )
        state["approval_id"] = approval["approval_id"]
        state["artifacts"]["approval"] = f"approvals/{approval_path.name}"
        state["action_receipts"] = receipts
        state["status"] = STATUS_COMPLETED
        state["outcome"] = "BATCH_REVIEWED_SIMULATED"
        state["updated_at"] = utc_now()
        self.store.save_state(state)
        self.store.append_trace(
            run_id,
            "state_transition",
            from_status=STATUS_WAITING_FOR_APPROVAL,
            to_status=STATUS_COMPLETED,
        )
        return self.view(run_id)

    def _simulate_action(
        self,
        run_id: str,
        dataset_id: str,
        proposal: str,
    ) -> dict[str, Any]:
        action = (
            "SIMULATE_PUBLISH"
            if proposal == "PUBBLICA"
            else "SIMULATE_PUBLISH_WITH_CONDITIONS"
        )
        key = sha256_value(f"{run_id}:{dataset_id}:{action}")[:24]
        path = self.store.action_path(run_id, key)
        if path_exists(path):
            receipt = read_json(path)
            self.store.append_trace(
                run_id,
                "action_replay_deduplicated",
                dataset_id=dataset_id,
                idempotency_key=key,
            )
            return receipt
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "kind": "action_receipt",
            "run_id": run_id,
            "dataset_id": dataset_id,
            "action": action,
            "idempotency_key": key,
            "effect_mode": "SIMULATED_FILE_ONLY",
            "status": "NOT_SENT",
            "created_at": utc_now(),
        }
        atomic_write_json(path, receipt)
        self.store.append_trace(
            run_id,
            "action_simulated",
            dataset_id=dataset_id,
            action=action,
            idempotency_key=key,
            effect_mode="SIMULATED_FILE_ONLY",
            status="NOT_SENT",
        )
        return receipt

    def resume(self, run_id: str) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            self._recover_import_locked(run_id)
            return self._resume_locked(run_id)

    def _resume_locked(self, run_id: str) -> dict[str, Any]:
        state = self.store.load_state(run_id)
        self._assert_design(state)
        for artifact in (
            "raw_inventory",
            "normalized_evidence",
            "deterministic_gates",
        ):
            name = state["artifacts"].get(artifact)
            if not name:
                raise LabError("corrupt_state", f"Artefatto mancante: {artifact}")
            read_json(self.store.artifact_path(run_id, name))
        if state["status"] == STATUS_WAITING_FOR_AI:
            self._active_request(state)
        elif state["status"] == STATUS_WAITING_FOR_APPROVAL:
            if not state.get("accepted_response_id") or not state.get("decisions"):
                raise LabError("corrupt_state", "Response o decisioni mancanti.")
            read_json(
                self.store.response_path(
                    run_id, state["accepted_response_id"]
                )
            )
        elif state["status"] == STATUS_COMPLETED:
            if not state.get("approval_id"):
                raise LabError("corrupt_state", "Approval mancante.")
            read_json(self.store.approval_path(run_id, state["approval_id"]))
            for relative in state["action_receipts"]:
                read_json(self.store.run_dir(run_id) / relative)
        else:
            raise LabError("corrupt_state", f"Stato non riprendibile: {state['status']}")
        self.store.trace(run_id)
        return self.view(run_id)

    def view(self, run_id: str) -> dict[str, Any]:
        with self.store.run_lock(run_id):
            self._recover_import_locked(run_id)
            return self._view_locked(run_id)

    def _view_locked(self, run_id: str) -> dict[str, Any]:
        state = self.store.load_state(run_id)
        self._assert_design(state)
        request = (
            self._active_request(state)
            if state.get("active_request_id")
            else None
        )
        from .approval_tasks import ApprovalTasks
        return {
            "approval_requests": ApprovalTasks(self, run_id).view(),
            "state": state,
            "ai_execution_mode": self.design["ai_delegation"]["execution_mode"],
            "workspace": str(self.store.workspace),
            "agent_session_status": (
                read_json(self.store.run_dir(run_id) / "agent/session.json")["status"]
                if path_is_file(self.store.run_dir(run_id) / "agent/session.json") else None
            ),
            "raw_inventory": read_json(
                self.store.artifact_path(run_id, "raw_inventory.json")
            ),
            "normalized": (
                read_json(self.store.artifact_path(run_id, "approval_reassessment.json"))["normalized"]
                if state["artifacts"].get("approval_reassessment")
                else read_json(self.store.artifact_path(run_id, "normalized_evidence.json"))
            ),
            "active_request": request,
            "response_template": (
                self.response_template(run_id)
                if state["status"] == STATUS_WAITING_FOR_AI
                else None
            ),
            "decisions": state["decisions"],
            "trace": self.store.trace(run_id),
        }

    def list_runs(self) -> list[dict[str, Any]]:
        return self.store.list_runs()

    def create_submission(
        self,
        run_ids: list[str],
        output_path: Path,
    ) -> dict[str, Any]:
        manifest = self._submission_manifest(run_ids)
        atomic_write_json(output_path.resolve(), manifest)
        return manifest

    def _submission_project_files(
        self,
    ) -> list[tuple[Path, str, str]]:
        if self.participant_root is None:
            return []
        from .preflight import run_preflight
        from .spec_bridge import load_frozen_design

        current_design = load_frozen_design(self.participant_root)
        if current_design["design_sha256"] != self.design["design_sha256"]:
            raise LabError(
                "submission_design_mismatch",
                "La consegna usa un design diverso dai run selezionati.",
            )
        preflight = run_preflight(self.participant_root)
        if preflight["status"] != "READY_TO_SUBMIT":
            raise LabError(
                "submission_not_ready",
                f"Preflight {preflight['status']}: completa challenge e report.",
            )

        entries: list[tuple[Path, str, str]] = []
        exact = (
            (
                "templates/workflow_spec_compilabile.docx",
                "spec/workflow_spec_compilabile.docx",
                "human_spec",
            ),
            (
                "build/spec/workflow_design.json",
                "spec/workflow_design.json",
                "runtime_design",
            ),
            (
                "build/spec/spec_freeze_receipt.json",
                "spec/spec_freeze_receipt.json",
                "freeze_receipt",
            ),
            (
                "build/spec/workflow_design_summary.txt",
                "spec/workflow_design_summary.txt",
                "human_summary",
            ),
            (
                "build/ai/ai_build_brief.txt",
                "ai/ai_build_brief.txt",
                "ai_handoff",
            ),
            (
                "reports/break_report.md",
                "reports/break_report.md",
                "challenge_report",
            ),
            (
                "reports/workflow_post_mortem.md",
                "reports/workflow_post_mortem.md",
                "post_mortem",
            ),
        )
        for source_name, archive_name, role in exact:
            source = self.participant_root / source_name
            if not path_is_file(source):
                raise LabError(
                    "missing_submission_artifact",
                    f"Artefatto richiesto: {source_name}.",
                )
            entries.append((source, archive_name, role))

        # Extension evidence is included when performed; never fabricate a missing demo.
        for name in ("coordination_evidence.json", "mcp_trace.json"):
            source = self.participant_root / "reports" / name
            if path_is_file(source):
                entries.append((source, f"reports/{name}", "run_evidence"))

        for source_name, archive_name, role in (
            ("agent/EVIDENZE_PARTECIPANTE.md", "agent/EVIDENZE_PARTECIPANTE.md", "participant_observation"),
            ("agent/VERIFICA_POSTAZIONE.md", "agent/VERIFICA_POSTAZIONE.md", "host_verification"),
            ("build/agent/readiness_receipt.json", "agent/readiness_receipt.json", "implementation_readiness"),
        ):
            source = self.participant_root / source_name
            if path_is_file(source):
                entries.append((source, archive_name, role))

        directories = (
            ("workflow", "workflow", "participant_code"),
            ("tests", "tests", "provided_tests"),
            ("tests_custom", "tests_custom", "participant_tests"),
            (
                "workspace/challenges",
                "challenges",
                "synthetic_challenges",
            ),
        )
        for source_name, archive_root, role in directories:
            source_root = self.participant_root / source_name
            for source in sorted(
                walk_files(source_root)
            ):
                if (
                    "__pycache__" in source.parts
                    or source.suffix.casefold() in {".pyc", ".pyo"}
                ):
                    continue
                relative = source.relative_to(source_root).as_posix()
                entries.append(
                    (source, f"{archive_root}/{relative}", role)
                )
        return entries

    def _submission_manifest(
        self,
        run_ids: list[str],
    ) -> dict[str, Any]:
        if not run_ids:
            raise LabError("empty_submission", "Almeno un run richiesto.")
        artifacts: list[dict[str, str]] = []
        for run_id in run_ids:
            state = self.store.load_state(run_id)
            self._assert_design(state)
            if state["status"] != STATUS_COMPLETED:
                raise LabError(
                    "incomplete_submission_run",
                    f"{run_id} non è COMPLETED.",
                )
            run_dir = self.store.run_dir(run_id)
            for path in sorted(walk_files(run_dir)):
                if ".tmp" not in path.name and path.name != ".run.lock":
                    self.store._contained(path, run_dir)
                    artifacts.append(
                        {
                            "path": (
                                f"runs/{run_id}/"
                                f"{path.relative_to(run_dir).as_posix()}"
                            ),
                            "sha256": sha256_file(path),
                            "role": "run_evidence",
                        }
                    )
        project_files = self._submission_project_files()
        for source, archive_name, role in project_files:
            artifacts.append(
                {
                    "path": archive_name,
                    "sha256": sha256_file(source),
                    "role": role,
                }
            )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "kind": "submission_manifest",
            "submission_id": identifier("SUB"),
            "run_ids": run_ids,
            "spec_id": self.design["spec_id"],
            "design_sha256": self.design["design_sha256"],
            "source_docx_sha256_at_freeze": self.design[
                "source_docx_sha256"
            ],
            "source_docx_sha256_at_submit": (
                sha256_file(
                    self.participant_root
                    / "templates/workflow_spec_compilabile.docx"
                )
                if self.participant_root
                else self.design["source_docx_sha256"]
            ),
            "artifacts": artifacts,
            "created_at": utc_now(),
            "human_review_required": True,
        }
        return manifest

    def create_submission_archive(
        self,
        run_ids: list[str],
        output_path: Path,
    ) -> dict[str, Any]:
        output = output_path.resolve()
        if output.suffix.casefold() != ".zip":
            raise LabError(
                "invalid_submission_archive",
                "La consegna human-first deve avere estensione .zip.",
            )
        manifest = self._submission_manifest(run_ids)
        manifest_payload = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        make_dirs(output.parent)
        fixed_time = (2026, 7, 28, 0, 0, 0)
        with ZipFile(
            os_fspath(output),
            "w",
            compression=ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            manifest_info = ZipInfo("submission_manifest.json", fixed_time)
            manifest_info.compress_type = ZIP_DEFLATED
            manifest_info.external_attr = 0o100644 << 16
            archive.writestr(manifest_info, manifest_payload)
            for source, archive_name, _role in self._submission_project_files():
                info = ZipInfo(archive_name, fixed_time)
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, read_bytes(source))
            for run_id in run_ids:
                run_dir = self.store.run_dir(run_id)
                for path in sorted(
                    walk_files(run_dir)
                ):
                    if ".tmp" in path.name or path.name == ".run.lock":
                        continue
                    self.store._contained(path, run_dir)
                    relative = path.relative_to(run_dir).as_posix()
                    info = ZipInfo(f"runs/{run_id}/{relative}", fixed_time)
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, read_bytes(path))
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "submission_archive_receipt",
            "archive": str(output),
            "archive_sha256": sha256_file(output),
            "run_ids": run_ids,
            "artifacts": len(manifest["artifacts"]),
            "human_review_required": True,
        }
