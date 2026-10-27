from __future__ import annotations

from typing import Any

from meridiano_lab.utils import SCHEMA_VERSION, parse_timestamp, sha256_value


def evidence_record(
    *,
    dataset_id: str,
    field: str,
    value: Any,
    source_id: str,
    source_path: str,
    source_record_id: str,
    observed_at: str,
    authority_scope: str,
    status: str = "FACT",
    raw_hash: str | None = None,
) -> dict[str, Any]:
    """Costruisce un record di provenienza conforme al contratto fornito."""
    identity = f"{dataset_id}:{field}:{source_id}:{source_record_id}"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "normalized_evidence",
        "evidence_id": f"EVID-{sha256_value(identity)[:20]}",
        "dataset_id": dataset_id,
        "field": field,
        "value": value,
        "source_id": source_id,
        "source_path": source_path,
        "source_record_id": source_record_id,
        "observed_at": observed_at,
        "authority_scope": authority_scope,
        "freshness": "CURRENT",
        "status": status,
        "raw_hash": raw_hash or sha256_value(value),
        "normalization_version": "participant-1.0",
    }


def latest(rows: list[dict[str, Any]], timestamp_field: str) -> dict[str, Any] | None:
    return max(
        rows,
        key=lambda row: parse_timestamp(str(row[timestamp_field]), timestamp_field),
        default=None,
    )


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}
