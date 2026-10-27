from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import LabError


SCHEMA_VERSION = "1.0"


def os_fspath(path: Path) -> str:
    """Percorso pronto per le API del sistema operativo.

    Su Windows antepone il prefisso di percorso esteso ``\\\\?\\`` così che le
    letture e scritture del laboratorio funzionino anche quando il pacchetto è
    estratto in cartelle molto profonde (ad es. sincronizzate su OneDrive) che
    superano il limite storico MAX_PATH di 260 caratteri. Su altri sistemi
    restituisce il percorso invariato.
    """
    text = os.fspath(path)
    if os.name != "nt":
        return text
    absolute = os.path.abspath(text)
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        # UNC \\server\share -> \\?\UNC\server\share
        return "\\\\?\\UNC" + absolute[1:]
    return "\\\\?\\" + absolute


def path_exists(path: Path) -> bool:
    return os.path.exists(os_fspath(path))


def path_is_file(path: Path) -> bool:
    return os.path.isfile(os_fspath(path))


def path_is_dir(path: Path) -> bool:
    return os.path.isdir(os_fspath(path))


def walk_files(root: Path):
    """File ricorsivi con percorsi estesi, senza seguire collegamenti a directory."""
    extended = Path(os_fspath(root))

    def fail(error: OSError) -> None:
        raise error

    if not path_exists(root):
        return
    for directory, _folders, names in os.walk(extended, onerror=fail):
        relative = Path(directory).relative_to(extended)
        for name in names:
            path = root / relative / name
            if path_is_file(path):
                yield path


def make_dirs(path: Path) -> None:
    os.makedirs(os_fspath(path), exist_ok=True)


def read_bytes(path: Path) -> bytes:
    with open(os_fspath(path), "rb") as handle:
        return handle.read()


def read_text(path: Path) -> str:
    with open(os_fspath(path), encoding="utf-8") as handle:
        return handle.read()


def remove_file(path: Path) -> None:
    try:
        os.remove(os_fspath(path))
    except FileNotFoundError:
        pass


def _silent_unlink(path: Path) -> None:
    try:
        os.remove(os_fspath(path))
    except FileNotFoundError:
        pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def identifier(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(os_fspath(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(os_fspath(path), encoding="utf-8") as handle:
            value = json.loads(handle.read())
    except FileNotFoundError as exc:
        raise LabError("missing_artifact", f"File mancante: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LabError("invalid_json", f"JSON non valido in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LabError("invalid_json_type", f"Oggetto JSON atteso in {path}.")
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    os.makedirs(os_fspath(path.parent), exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with open(os_fspath(temporary), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(8):
        try:
            os.replace(os_fspath(temporary), os_fspath(path))
            return
        except PermissionError:
            if attempt == 7:
                _silent_unlink(temporary)
                raise
            # OneDrive e alcuni antivirus possono trattenere brevemente il file
            # appena sincronizzato. Il backoff resta sotto due secondi complessivi.
            time.sleep(min(0.05 * (2**attempt), 0.4))


def atomic_write_text(path: Path, value: str) -> None:
    os.makedirs(os_fspath(path.parent), exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = value.rstrip() + "\n"
    with open(os_fspath(temporary), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    for attempt in range(8):
        try:
            os.replace(os_fspath(temporary), os_fspath(path))
            return
        except PermissionError:
            if attempt == 7:
                _silent_unlink(temporary)
                raise
            time.sleep(min(0.05 * (2**attempt), 0.4))


def parse_timestamp(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise LabError("invalid_timestamp", f"{field} non è un timestamp ISO valido.") from exc


def require_keys(value: dict[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing:
        raise LabError("contract_violation", f"{label}: campi mancanti {sorted(missing)}.")
    if extra:
        raise LabError("contract_violation", f"{label}: campi non ammessi {sorted(extra)}.")
