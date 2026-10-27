from __future__ import annotations

import csv
import json
import re
import sqlite3
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .errors import LabError
from .utils import read_json, sha256_file, sha256_value


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LabError("invalid_ndjson", f"{path}:{number}: {exc}") from exc
        if not isinstance(value, dict):
            raise LabError("invalid_ndjson", f"{path}:{number}: oggetto atteso.")
        rows.append(value)
    return rows


def _emails(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=("plain",))
        text = body.get_content() if body else message.get_payload()
        dataset_ref = str(message.get("X-Meridiano-Dataset", "")).strip()
        if not dataset_ref:
            raise LabError("missing_dataset_ref", f"Header X-Meridiano-Dataset mancante: {path}")
        date_header = str(message.get("Date", ""))
        try:
            observed_at = parsedate_to_datetime(date_header).isoformat()
        except (TypeError, ValueError) as exc:
            raise LabError("invalid_email_date", f"Data email non valida: {path}") from exc
        rows.append(
            {
                "source_id": str(message.get("Message-ID", "")).strip("<>"),
                "dataset_ref": dataset_ref,
                "subject": str(message.get("Subject", "")),
                "text": str(text).strip(),
                "observed_at": observed_at,
                "source_path": path.relative_to(root).as_posix(),
                "raw_hash": sha256_file(path),
            }
        )
    return rows


def _calendar(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0]] = value
    timezone = ZoneInfo("Europe/Rome")
    output = []
    for event in events:
        start = datetime.strptime(event["DTSTART"], "%Y%m%dT%H%M%S").replace(tzinfo=timezone)
        end = datetime.strptime(event["DTEND"], "%Y%m%dT%H%M%S").replace(tzinfo=timezone)
        output.append(
            {
                "event_id": event["UID"],
                "dataset_ref": event.get("X-MERIDIANO-DATASET", "ALL"),
                "summary": event["SUMMARY"],
                "start_at": start.isoformat(),
                "end_at": end.isoformat(),
                "source_path": path.name,
            }
        )
    return output


def _sqlite(path: Path) -> dict[str, list[dict[str, Any]]]:
    connection = sqlite3.connect(path)
    try:
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise LabError("sqlite_integrity", f"Integrity check fallito: {path}")
        names = [
            "dataset_registry",
            "dataset_versions",
            "license_bindings",
            "approval_events",
            "audit_events",
        ]
        return {
            name: [
                dict(row)
                for row in connection.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall()
            ]
            for name in names
        }
    finally:
        connection.close()


def _registry_json(path: Path) -> dict[str, list[dict[str, Any]]]:
    value = read_json(path)
    if value.get("source_id") != "MER-REGISTRY" or not value.get("generated_from_same_snapshot"):
        raise LabError("invalid_registry_fallback", f"Fallback non equivalente: {path}")
    tables = value.get("tables")
    if not isinstance(tables, dict):
        raise LabError("invalid_registry_fallback", f"Tabelle mancanti: {path}")
    return tables


def _validate_overlay(value: dict[str, Any]) -> None:
    if value.get("schema_version") != "1.0" or value.get("kind") != "incident_overlay":
        raise LabError("invalid_overlay", "Header overlay non valido.")
    if not value.get("overlay_id") or not isinstance(value.get("operations"), list):
        raise LabError("invalid_overlay", "ID o operations overlay mancanti.")
    for operation in value["operations"]:
        if operation.get("op") not in {"add_text_evidence", "add_approval_event"}:
            raise LabError("invalid_overlay", f"Operazione non ammessa: {operation.get('op')}")
        if not re.fullmatch(r"DS-\d{2}", str(operation.get("dataset_id", ""))):
            raise LabError("invalid_overlay", "dataset_id overlay non valido.")
        if not isinstance(operation.get("record"), dict):
            raise LabError("invalid_overlay", "record overlay non valido.")


def load_case(
    case_root: Path,
    registry_backend: str = "sqlite",
    overlay_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    case_root = case_root.resolve()
    manifest = read_json(case_root / "case_manifest.json")
    if manifest.get("kind") != "case_manifest" or manifest.get("schema_version") != "1.0":
        raise LabError("invalid_case_manifest", "Header manifest non valido.")
    if manifest.get("contains_real_personal_data") is not False:
        raise LabError("unsafe_case", "Il laboratorio accetta soltanto dati sintetici.")
    for relative, expected_hash in manifest.get("source_hashes", {}).items():
        path = (case_root / relative).resolve()
        try:
            path.relative_to(case_root)
        except ValueError as exc:
            raise LabError("unsafe_source_path", f"Path fuori dal caso: {relative}") from exc
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise LabError("source_hash_mismatch", f"Fonte mancante o modificata: {relative}")

    structured = case_root / "raw" / "structured"
    text_paths = sorted((case_root / "raw" / "unstructured").glob("*.eml"))
    if registry_backend == "sqlite":
        registry = _sqlite(case_root / "raw" / "registry" / "meridiano_registry.sqlite")
    elif registry_backend == "json":
        registry = _registry_json(
            case_root / "raw" / "registry" / "meridiano_registry_readonly.json"
        )
    else:
        raise LabError("invalid_registry_backend", "Usare sqlite oppure json.")

    bundle: dict[str, Any] = {
        "metadata": _csv(structured / "metadata_catalog.csv"),
        "quality_events": _ndjson(structured / "quality_events.ndjson"),
        "license_records": _csv(structured / "license_register.csv"),
        "tickets": _csv(structured / "service_tickets.csv"),
        "calendar_events": _calendar(structured / "release_calendar.ics"),
        "text_evidence": _emails(text_paths, case_root),
        "registry": registry,
        "overlay": None,
    }

    if overlay_path is not None:
        overlay = read_json(overlay_path.resolve())
        _validate_overlay(overlay)
        known = set(manifest["dataset_ids"])
        for operation in overlay["operations"]:
            if operation["dataset_id"] not in known:
                raise LabError("foreign_overlay_dataset", operation["dataset_id"])
            record = dict(operation["record"])
            record["dataset_ref"] = operation["dataset_id"]
            if operation["op"] == "add_text_evidence":
                required = {"source_id", "text", "observed_at"}
                if not required.issubset(record):
                    raise LabError("invalid_overlay", "Evidenza testuale overlay incompleta.")
                record.setdefault("subject", overlay["title"])
                record.setdefault("source_path", f"overlay://{overlay['overlay_id']}")
                record["raw_hash"] = sha256_value(record)
                bundle["text_evidence"].append(record)
            else:
                required = {
                    "approval_event_id",
                    "scope",
                    "actor_role",
                    "decision",
                    "decided_at",
                    "evidence_ref",
                }
                if not required.issubset(record):
                    raise LabError("invalid_overlay", "Approval overlay incompleta.")
                record["object_id"] = operation["dataset_id"]
                bundle["registry"]["approval_events"].append(record)
        bundle["overlay"] = {
            "overlay_id": overlay["overlay_id"],
            "overlay_version": overlay["overlay_version"],
            "sha256": sha256_file(overlay_path),
            "path": str(overlay_path.resolve()),
        }

    inventory = {
        "schema_version": "1.0",
        "kind": "raw_inventory",
        "case_id": manifest["case_id"],
        "registry_backend": registry_backend,
        "counts": {
            key: len(value)
            for key, value in bundle.items()
            if isinstance(value, list)
        },
        "registry_counts": {key: len(value) for key, value in registry.items()},
        "source_hashes": manifest["source_hashes"],
        "overlay": bundle["overlay"],
    }
    return manifest, {"bundle": bundle, "inventory": inventory}
