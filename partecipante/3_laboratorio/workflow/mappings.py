from __future__ import annotations

from typing import Any, Callable

from meridiano_lab.errors import LabError
from meridiano_lab.utils import sha256_value

from .common import evidence_record, latest


Canonicalize = Callable[[str], str]
MappingResult = tuple[dict[str, Any], list[dict[str, Any]]]


def canonicalize_dataset(manifest: dict[str, Any], value: str) -> str:
    """Normalizza un alias dichiarato e fallisce chiuso sugli alias estranei."""
    try:
        dataset_id = manifest["aliases"][value.strip()]
    except (AttributeError, KeyError) as exc:
        raise LabError("unknown_dataset_alias", str(value)) from exc
    if dataset_id not in manifest["dataset_ids"]:
        raise LabError("foreign_dataset_alias", str(value))
    return dataset_id


def map_metadata(
    rows: list[dict[str, Any]],
    canonicalize: Canonicalize,
) -> MappingResult:
    """Mappa il catalogo e crea evidenze campo-per-campo."""
    fields = (
        "title",
        "authors",
        "description",
        "spatial_coverage",
        "temporal_coverage",
        "format",
        "version",
    )
    fragments: dict[str, Any] = {}
    evidence: list[dict[str, Any]] = []
    for row in rows:
        dataset_id = canonicalize(row["dataset_id"])
        fragments[dataset_id] = dict(row, dataset_id=dataset_id)
        for field in fields:
            value = row.get(field, "")
            evidence.append(
                evidence_record(
                    dataset_id=dataset_id,
                    field=f"metadata.{field}",
                    value=value,
                    source_id="metadata_catalog",
                    source_path="raw/structured/metadata_catalog.csv",
                    source_record_id=dataset_id,
                    observed_at=row["updated_at"],
                    authority_scope="metadata",
                    status="FACT" if str(value).strip() else "UNKNOWN",
                    raw_hash=sha256_value(row),
                )
            )
    return fragments, evidence


def map_quality(
    rows: list[dict[str, Any]],
    canonicalize: Canonicalize,
) -> MappingResult:
    """[TODO-02] Deduplica event_id, conserva il record più recente e la provenienza."""
    raise LabError("todo_02", "Implementare map_quality.")


def map_licenses(
    rows: list[dict[str, Any]],
    canonicalize: Canonicalize,
) -> MappingResult:
    """Seleziona il record corrente senza calcolare il gate licenza."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not row.get("superseded_by"):
            dataset_id = canonicalize(row["dataset_id"])
            grouped.setdefault(dataset_id, []).append(
                dict(row, dataset_id=dataset_id)
            )
    fragments: dict[str, Any] = {}
    evidence: list[dict[str, Any]] = []
    for dataset_id, candidates in grouped.items():
        current = latest(candidates, "updated_at")
        fragments[dataset_id] = current
        if current:
            evidence.append(
                evidence_record(
                    dataset_id=dataset_id,
                    field="license.current",
                    value=current,
                    source_id="license_register",
                    source_path="raw/structured/license_register.csv",
                    source_record_id=current["license_record_id"],
                    observed_at=current["updated_at"],
                    authority_scope="license",
                    raw_hash=sha256_value(current),
                )
            )
    return fragments, evidence


def map_text_evidence(
    rows: list[dict[str, Any]],
    canonicalize: Canonicalize,
) -> MappingResult:
    """[TODO-03] Associa EML grezze al dataset e produce evidence_ref per l'AI."""
    raise LabError("todo_03", "Implementare map_text_evidence.")


def map_registry(
    registry: dict[str, list[dict[str, Any]]],
    canonicalize: Canonicalize,
) -> MappingResult:
    """[TODO-04] Mappa versioni, binding e approval mantenendo gli scope distinti."""
    raise LabError("todo_04", "Implementare map_registry.")
