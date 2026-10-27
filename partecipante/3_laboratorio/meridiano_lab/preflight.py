from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from .agent_readiness import verify_readiness
from .errors import LabError
from .readers import load_case
from .spec_bridge import freeze_status, load_frozen_design


TODO_PATTERN = re.compile(r"\[TODO-\d{2}\]")
EXPECTED_TODOS = [f"[TODO-{index:02d}]" for index in range(1, 13)]

# Limite storico di Windows sui percorsi (MAX_PATH). Le scritture/letture atomiche
# usano già il prefisso esteso \\?\ (vedi utils.os_fspath); resta però qualche
# operazione non estesa (creazione cartelle dei run, backend sqlite) che non
# supera il limite. Stima del segmento relativo più profondo dal root di
# installazione oltre il quale queste operazioni iniziano a fallire: misurata
# empiricamente (artefatto più profondo ~119, guasto osservato con root ~173),
# tenuta più bassa per avvisare con margine e senza falsi allarmi sui percorsi
# che funzionano.
_WINDOWS_MAX_PATH = 260
_DEEPEST_RUNTIME_RELATIVE = 105


def _long_path_report(participant_root: Path) -> dict[str, Any]:
    install_path = str(participant_root)
    length = len(install_path)
    projected = length + 1 + _DEEPEST_RUNTIME_RELATIVE
    on_windows = os.name == "nt"
    ok = (not on_windows) or projected < _WINDOWS_MAX_PATH
    report: dict[str, Any] = {
        "install_path": install_path,
        "install_path_length": length,
        "projected_deepest_path": projected,
        "windows_max_path": _WINDOWS_MAX_PATH,
        "long_path_ok": ok,
    }
    if not ok:
        report["hint"] = (
            "Percorso di installazione troppo profondo per Windows "
            f"(previsti ~{projected} caratteri, limite {_WINDOWS_MAX_PATH}). "
            "Estrai il laboratorio in una cartella con percorso più corto "
            "(es. C:\\meridiano_lab) e riesegui il preflight."
        )
    return report


def _completed_runs(workspace: Path) -> list[str]:
    result: list[str] = []
    runs = workspace / "runs"
    if not runs.is_dir():
        return result
    for state in runs.glob("*/state.json"):
        try:
            text = state.read_text(encoding="utf-8")
        except OSError:
            continue
        if '"status": "COMPLETED"' in text:
            result.append(state.parent.name)
    return sorted(result)


def run_preflight(participant_root: Path) -> dict[str, Any]:
    participant_root = participant_root.resolve()
    case_root = participant_root / "case"
    prompt = participant_root / "workflow" / "prompts" / "classify_evidence.txt"
    workflow_files = sorted((participant_root / "workflow").rglob("*.py"))
    workflow_files.append(prompt)
    workflow_files.append(participant_root / "workflow/agent_config.json")
    todo_ids: list[str] = []
    forbidden_hits: list[str] = []
    for path in workflow_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        todo_ids.extend(TODO_PATTERN.findall(text))
        retired_runtime = "control" + "_" + "room"
        retired_prototype = "workflow" + "_" + "lab" + "_" + "spike"
        for forbidden in (
            retired_runtime,
            retired_prototype,
            "Modulo_6.lab",
            f"Modulo_6.{retired_runtime}",
        ):
            if forbidden in text:
                forbidden_hits.append(f"{path.name}:{forbidden}")

    manifest, loaded = load_case(case_root, registry_backend="sqlite")
    spec = freeze_status(participant_root)
    todo_sequence_valid = (
        len(todo_ids) == len(set(todo_ids))
        and set(todo_ids).issubset(set(EXPECTED_TODOS))
    )
    build_artifacts = {
        "design": participant_root / "build/spec/workflow_design.json",
        "receipt": participant_root / "build/spec/spec_freeze_receipt.json",
        "ai_brief": participant_root / "build/ai/ai_build_brief.txt",
        "prompt_pack": participant_root / "build/ai/todo_prompt_pack",
        "spec_fixture": participant_root
        / "tests_custom/generated_spec_fixture.json",
    }
    artifacts_ready = all(path.exists() for path in build_artifacts.values())
    completed_runs = _completed_runs(participant_root / "workspace")
    challenge_ready = any(
        (path / "challenge_manifest.json").is_file()
        for path in (participant_root / "workspace/challenges").glob("*")
    ) if (participant_root / "workspace/challenges").is_dir() else False
    report_paths = [
        participant_root / relative
        for relative in (
            "reports/break_report.md",
            "reports/workflow_post_mortem.md",
        )
    ]
    reports_ready = all(path.is_file() for path in report_paths) and all(
        "[COMPILA]" not in path.read_text(encoding="utf-8")
        for path in report_paths
    )
    configuration: dict[str, Any] = {"valid": False, "code": "agent_config_required"}
    execution_mode = None
    if spec["valid"]:
        from .agent_config import load_agent_config
        design = load_frozen_design(participant_root)
        execution_mode = design["ai_delegation"]["execution_mode"]
        try:
            load_agent_config(participant_root, design)
            configuration = {"valid": True}
        except LabError as exc:
            configuration.update(code=exc.code, message=exc.message)
    agent_readiness: dict[str, Any] = {"valid": False, "code": "agent_not_ready"}
    if spec["valid"] and not todo_ids:
        try:
            receipt = verify_readiness(participant_root, load_frozen_design(participant_root))
            agent_readiness = {
                "valid": True,
                "suite_version": receipt["suite_version"],
                "implementation_sha256": receipt["implementation_sha256"],
                "design_sha256": receipt["design_sha256"],
            }
        except LabError as exc:
            agent_readiness.update(code=exc.code, message=exc.message)

    if not spec["valid"]:
        status = {
            "spec_not_frozen": "SPEC_NOT_FROZEN",
            "spec_drift": "SPEC_DRIFT",
        }.get(str(spec.get("code")), "SPEC_INVALID")
    elif not artifacts_ready or not todo_sequence_valid:
        status = "BUILD_SPEC_MISMATCH"
    elif len(todo_ids) == len(EXPECTED_TODOS):
        status = "READY_FOR_AI_BUILD"
    elif todo_ids:
        status = "BUILD_IN_PROGRESS"
    elif not configuration["valid"]:
        status = "AGENT_CONFIGURATION_REQUIRED"
    elif not completed_runs:
        status = "READY_FOR_BASELINE"
    elif not challenge_ready:
        status = "READY_FOR_CHALLENGES"
    elif challenge_ready and reports_ready:
        status = "READY_TO_SUBMIT"
    else:
        status = "READY_FOR_CHALLENGES"

    return {
        "status": status,
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 10),
        "environment": _long_path_report(participant_root),
        "case_id": manifest["case_id"],
        "datasets": manifest["dataset_ids"],
        "source_counts": loaded["inventory"]["counts"],
        "registry_counts": loaded["inventory"]["registry_counts"],
        "spec": spec,
        "todo_count": len(todo_ids),
        "todo_ids": sorted(todo_ids),
        "todo_contract_valid": todo_sequence_valid,
        "build_artifacts_ready": artifacts_ready,
        "agent_readiness": agent_readiness,
        "ai_execution_mode": execution_mode,
        "agent_configuration": configuration,
        "completed_runs": completed_runs,
        "challenge_ready": challenge_ready,
        "reports_ready": reports_ready,
        "forbidden_import_hits": forbidden_hits,
        "offline_runtime": True,
        "simulated_effects_only": manifest["policy"]["simulated_effects_only"],
        "human_review_required": manifest["policy"]["human_approval_required"],
    }
