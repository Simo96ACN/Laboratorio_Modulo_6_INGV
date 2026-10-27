"""Costruisce varianti facilitator-only con ID permutati.

Le varianti preservano i fatti e cambiano gli identificativi in ogni fonte,
incluso il registro SQLite. Non sono materiale partecipante.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replacement_map(dataset_id_map: dict[str, str]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for source, target in dataset_id_map.items():
        suffix = source.split("-", 1)[1]
        compact_target = target.replace("-", "")
        replacements[source] = target
        replacements[f"DS{suffix}"] = compact_target
        replacements[f"DATASET-{suffix}"] = f"ALIAS-{compact_target}"
    return replacements


def _replace(value: str, replacements: dict[str, str]) -> str:
    result = value
    placeholders: dict[str, str] = {}
    for index, (source, target) in enumerate(
        sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    ):
        placeholder = f"__MERIDIANO_VARIANT_{index:02d}__"
        result = result.replace(source, placeholder)
        placeholders[placeholder] = target
    for placeholder, target in placeholders.items():
        result = result.replace(placeholder, target)
    return result


def _rewrite_sqlite(path: Path, replacements: dict[str, str]) -> None:
    connection = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            if not row[0].startswith("sqlite_")
        ]
        for table in tables:
            columns = [
                row[1]
                for row in connection.execute(f'PRAGMA table_info("{table}")')
                if str(row[2]).upper() in {"TEXT", ""}
            ]
            rowids = [
                row[0]
                for row in connection.execute(f'SELECT rowid FROM "{table}"')
            ]
            for rowid in rowids:
                for column in columns:
                    current = connection.execute(
                        f'SELECT "{column}" FROM "{table}" WHERE rowid = ?',
                        (rowid,),
                    ).fetchone()[0]
                    if isinstance(current, str):
                        updated = _replace(current, replacements)
                        if updated != current:
                            connection.execute(
                                f'UPDATE "{table}" SET "{column}" = ? WHERE rowid = ?',
                                (updated, rowid),
                            )
        connection.commit()
    finally:
        connection.close()


def build_variant(
    baseline_case: Path,
    output_case: Path,
    definition: dict[str, Any],
) -> dict[str, Any]:
    baseline_case = baseline_case.resolve()
    output_case = output_case.resolve()
    if output_case.exists():
        raise FileExistsError(output_case)
    shutil.copytree(baseline_case, output_case)
    replacements = _replacement_map(definition["dataset_id_map"])

    for path in sorted(output_case.rglob("*")):
        if not path.is_file() or path.name in {
            "case_manifest.json",
            "case_hashes.json",
        }:
            continue
        if path.suffix == ".sqlite":
            _rewrite_sqlite(path, replacements)
        else:
            text = path.read_text(encoding="utf-8")
            path.write_text(
                _replace(text, replacements),
                encoding="utf-8",
                newline="\n",
            )

    manifest_path = output_case / "case_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_id"] = definition["variant_id"]
    manifest["scenario_version"] = definition["variant_id"]
    manifest["dataset_ids"] = [
        definition["dataset_id_map"][dataset_id]
        for dataset_id in manifest["dataset_ids"]
    ]
    manifest["aliases"] = {
        _replace(alias, replacements): definition["dataset_id_map"][canonical]
        for alias, canonical in manifest["aliases"].items()
    }
    manifest["source_hashes"] = {
        relative: _sha256(output_case / relative)
        for relative in manifest["source_hashes"]
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    hash_manifest_path = output_case / "case_hashes.json"
    hash_manifest = json.loads(hash_manifest_path.read_text(encoding="utf-8"))
    hash_manifest["case_id"] = definition["variant_id"]
    hash_manifest["files"] = {
        relative: _sha256(output_case / relative)
        for relative in hash_manifest["files"]
        if relative != "case_hashes.json"
    }
    hash_manifest_path.write_text(
        json.dumps(hash_manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest
