"""Probe pubblici del contratto TODO-08, senza soluzioni o verita del caso.

La ricevuta registra soltanto le prove osservate sul codice locale. Non dimostra
purezza generale, correttezza semantica o isolamento da codice Python ostile.
"""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import LabError
from .utils import atomic_write_json, read_json, sha256_file, sha256_value, utc_now


SUITE_VERSION = "agent-validation-public-1"
RECEIPT_PATH = Path("build/agent/readiness_receipt.json")
TODO_PATTERN = re.compile(r"\[TODO-\d{2}\]")


def implementation_snapshot(participant_root: Path) -> dict[str, str]:
    """Inventario stabile del codice effettivo, esclusi cache e file generati."""
    root = participant_root.resolve()
    files = sorted((root / "workflow").rglob("*.py"))
    config = root / "workflow/agent_config.json"
    if config.is_file():
        files.append(config)
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in files}


def _assert_completed(participant_root: Path) -> None:
    files = list((participant_root / "workflow").rglob("*.py"))
    if not files or any(TODO_PATTERN.search(p.read_text(encoding="utf-8")) for p in files):
        raise LabError("agent_not_ready", "Completare i dodici TODO prima della sessione operativa.")


def public_validation_fixture(design: dict[str, Any]) -> dict[str, Any]:
    """Due dataset inventati: nessun risultato baseline, reveal o policy risolta."""
    minimum = int(design["policy_choices"]["minimum_independent_evidence"])
    dataset_ids = ["PUBLIC-SYNTH-A", "PUBLIC-SYNTH-B"]
    evidence = {
        dataset: [
            {
                "dataset_id": dataset,
                "evidence_ref": f"PUBLIC:{dataset}:{index}",
                "evidence_id": f"PUBLIC-{dataset}-{index}",
                "source_path": f"synthetic/{dataset}/independent-{index}.txt",
                "text": "Record sintetico per verificare il contratto, senza esito reale.",
                "observed_at": "2026-10-22T00:00:00Z",
            }
            for index in range(max(3, minimum))
        ]
        for dataset in dataset_ids
    }
    request = {
        "schema_version": "1.0", "kind": "ai_request",
        "run_id": "PUBLIC-RUN", "request_id": "PUBLIC-REQUEST",
        "node_id": "classify_evidence", "dataset_ids": dataset_ids,
        "prompt_hash": "public-synthetic", "payload_hash": "public-synthetic",
        "payload": {"evidence_by_dataset": evidence},
    }
    response = {
        "schema_version": "1.0", "kind": "ai_response",
        "run_id": request["run_id"], "request_id": request["request_id"],
        "node_id": request["node_id"], "prompt_hash": request["prompt_hash"],
        "payload_hash": request["payload_hash"],
        "response_id": "PUBLIC-RESPONSE", "created_at": "2026-10-22T00:00:00Z",
        "outputs": [
            {
                "dataset_id": dataset, "label": "UNKNOWN",
                "rationale": "Fixture sintetica: la classificazione reale resta da verificare.",
                "evidence_refs": [r["evidence_ref"] for r in evidence[dataset][:minimum]],
                "uncertainties": ["Non e una classificazione del caso Meridiano."],
            }
            for dataset in dataset_ids
        ],
    }
    normalized = {
        "schema_version": "1.0", "kind": "normalized_bundle",
        "dataset_ids": dataset_ids,
        "by_dataset": {d: {"texts": deepcopy(rows)} for d, rows in evidence.items()},
        "stats": {}, "normalization_version": "public-synthetic-1",
    }
    return {"request": request, "response": response, "normalized": normalized, "design": deepcopy(design)}


def _files_snapshot(root: Path | None) -> dict[str, str]:
    if root is None or not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): sha256_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.name != ".run.lock"
    }


def run_public_validation_probes(
    implementation: Any, design: dict[str, Any], *, observed_root: Path | None = None,
) -> dict[str, Any]:
    """Esegue il solo hook; non chiama decide, import, review o azioni simulate."""
    fixture = public_validation_fixture(design)
    before_files = _files_snapshot(observed_root)
    results: dict[str, str] = {}

    def invoke(name: str, response: dict[str, Any], *, rejects: bool = False) -> Any:
        inputs = deepcopy(fixture)
        inputs["response"] = deepcopy(response)
        before = deepcopy(inputs)
        before_object = deepcopy(getattr(implementation, "__dict__", {}))
        result = None
        rejected = False
        try:
            result = implementation.validate_ai_outputs(**inputs)
        except LabError:
            rejected = True
        except Exception as exc:
            raise LabError("agent_readiness_failed", f"Probe {name}: errore inatteso {type(exc).__name__}.") from exc
        if inputs != before or getattr(implementation, "__dict__", {}) != before_object:
            raise LabError("agent_readiness_failed", f"Probe {name}: il validatore modifica input o stato dell'implementazione.")
        if _files_snapshot(observed_root) != before_files:
            raise LabError("agent_readiness_failed", f"Probe {name}: modifica agli artefatti osservati.")
        if rejected != rejects:
            raise LabError("agent_readiness_failed", f"Probe {name}: atteso {'rifiuto' if rejects else 'successo'}.")
        if not rejects and (not isinstance(result, dict) or set(result) != set(fixture["request"]["dataset_ids"])):
            raise LabError("agent_readiness_failed", f"Probe {name}: mapping validato incompleto.")
        results[name] = "PASS"
        return result

    response = fixture["response"]
    first = invoke("positive", response)
    if invoke("repeat_without_mutation", response) != first:
        raise LabError("agent_readiness_failed", "Validazione ripetuta con risultato diverso.")
    omitted = deepcopy(response)
    omitted["outputs"].pop()
    invoke("missing_dataset", omitted, rejects=True)
    duplicate = deepcopy(response)
    duplicate["outputs"].append(deepcopy(duplicate["outputs"][0]))
    invoke("duplicate_dataset", duplicate, rejects=True)
    foreign = deepcopy(response)
    foreign["outputs"][0]["evidence_refs"] = deepcopy(response["outputs"][1]["evidence_refs"])
    invoke("cross_dataset_reference", foreign, rejects=True)
    insufficient = deepcopy(response)
    insufficient["outputs"][0]["evidence_refs"] = insufficient["outputs"][0]["evidence_refs"][:-1]
    invoke("insufficient_support", insufficient, rejects=True)
    if int(design["policy_choices"]["minimum_independent_evidence"]) > 1:
        repeated = deepcopy(response)
        refs = repeated["outputs"][0]["evidence_refs"]
        repeated["outputs"][0]["evidence_refs"] = [refs[0]] * len(refs)
        invoke("duplicate_support_is_not_independent", repeated, rejects=True)
    if design["interaction_policy"]["ai_validation"] == "strict":
        strict = deepcopy(response)
        strict["outputs"][0]["rationale"] = "Breve"
        invoke("strict_validation", strict, rejects=True)
    return {"suite_version": SUITE_VERSION, "probes": results, "status": "PASS"}


def create_readiness_receipt(
    participant_root: Path, implementation: Any, design: dict[str, Any], *, observed_root: Path | None = None,
) -> dict[str, Any]:
    root = participant_root.resolve()
    _assert_completed(root)
    snapshot = implementation_snapshot(root)
    report = run_public_validation_probes(implementation, design, observed_root=observed_root or root / "workspace")
    if implementation_snapshot(root) != snapshot:
        raise LabError("agent_readiness_failed", "Codice modificato durante le prove di readiness.")
    receipt = {
        "kind": "agent_readiness_receipt", "schema_version": "1.0",
        "created_at": utc_now(), "suite_version": SUITE_VERSION,
        "implementation_sha256": sha256_value(snapshot), "implementation_files": snapshot,
        "design_sha256": sha256_value(design), "spec_id": design["spec_id"],
        "report": report,
        "limits": "Probe sintetici pubblici: non certificano purezza generale, semantica o isolamento.",
    }
    atomic_write_json(root / RECEIPT_PATH, receipt)
    return receipt


def verify_readiness(participant_root: Path, design: dict[str, Any]) -> dict[str, Any]:
    root = participant_root.resolve()
    _assert_completed(root)
    path = root / RECEIPT_PATH
    if not path.is_file():
        raise LabError("agent_not_ready", "Ricevuta readiness assente: eseguire prepare-agent.")
    receipt = read_json(path)
    if (
        receipt.get("suite_version") != SUITE_VERSION
        or receipt.get("implementation_sha256") != sha256_value(implementation_snapshot(root))
        or receipt.get("design_sha256") != sha256_value(design)
        or receipt.get("report", {}).get("status") != "PASS"
    ):
        raise LabError("agent_readiness_drift", "Codice, design o suite diversi dalla ricevuta readiness: ripetere prepare-agent.")
    return receipt
