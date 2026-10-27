from __future__ import annotations

import json
import os
import re
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .errors import LabError
from .utils import (
    SCHEMA_VERSION, atomic_write_json, identifier, make_dirs, os_fspath, path_exists, path_is_dir, path_is_file,
    read_json, read_text, remove_file, utc_now,
)


RUN_ID_PATTERN = re.compile(r"^RUN-[a-f0-9]{32}$")
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
_HELD_LOCKS = threading.local()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Pubblica byte esatti: il digest della consegna precede ogni normalizzazione."""
    make_dirs(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(os_fspath(temporary), "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(os_fspath(temporary), os_fspath(path))
    finally:
        remove_file(temporary)


class RunStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.runs = self.workspace / "runs"
        make_dirs(self.runs)
        if self.runs.resolve() != self.runs:
            raise LabError("unsafe_run_path", "La directory runs non può essere un collegamento.")

    def _contained(self, path: Path, root: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise LabError("unsafe_run_path", str(path)) from exc
        return resolved

    @contextmanager
    def run_lock(self, run_id: str):
        """Unico lock rientrante per thread e interprocesso, rilasciato dall'OS.

        Il file resta sul disco: cancellarlo produrrebbe due domini di lock.
        Una mutazione concorrente riceve run_busy e può riprovare dopo il recupero.
        """
        directory = self.run_dir(run_id)
        if not path_is_dir(directory):
            raise LabError("missing_artifact", f"Run inesistente: {run_id}")
        key = str(directory)
        with _LOCKS_GUARD:
            mutex = _LOCKS.setdefault(key, threading.RLock())
        if not mutex.acquire(blocking=False):
            raise LabError("run_busy", f"Mutazione già in corso: {run_id}")
        held = getattr(_HELD_LOCKS, "paths", None)
        if held is None:
            held = _HELD_LOCKS.paths = set()
        handle = None
        locked = False
        nested = key in held
        try:
            if not nested:
                lock_path = self._contained(directory / ".run.lock", directory)
                handle = open(os_fspath(lock_path), "a+b")
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise LabError("run_busy", f"Mutazione già in corso: {run_id}") from exc
                locked = True
                held.add(key)
            yield
        finally:
            if locked:
                held.remove(key)
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            if handle is not None:
                handle.close()
            mutex.release()

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise LabError("invalid_run_id", "run_id non valido.")
        path = (self.runs / run_id).resolve()
        if path != self.runs / run_id:
            raise LabError("unsafe_run_path", "Il run non può essere un collegamento.")
        try:
            path.relative_to(self.runs)
        except ValueError as exc:
            raise LabError("unsafe_run_path", run_id) from exc
        return path

    def create(self, run_id: str) -> Path:
        path = self.run_dir(run_id)
        if path_exists(path):
            raise LabError("duplicate_run", run_id)
        for folder in ("ai_requests", "ai_responses", "approvals", "actions", "exchange"):
            make_dirs(path / folder)
        return path

    def state_path(self, run_id: str) -> Path:
        root = self.run_dir(run_id)
        return self._contained(root / "state.json", root)

    def trace_path(self, run_id: str) -> Path:
        root = self.run_dir(run_id)
        return self._contained(root / "trace.ndjson", root)

    def artifact_path(self, run_id: str, name: str) -> Path:
        if "/" in name or "\\" in name or name.startswith("."):
            raise LabError("invalid_artifact_name", name)
        root = self.run_dir(run_id)
        return self._contained(root / name, root)

    def request_path(self, run_id: str, request_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", request_id):
            raise LabError("invalid_request_id", request_id)
        root = self.run_dir(run_id)
        return self._contained(root / "ai_requests" / f"{request_id}.json", root)

    def response_path(self, run_id: str, response_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", response_id):
            raise LabError("invalid_response_id", response_id)
        root = self.run_dir(run_id)
        return self._contained(root / "ai_responses" / f"{response_id}.json", root)

    def approval_path(self, run_id: str, approval_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", approval_id):
            raise LabError("invalid_approval_id", approval_id)
        root = self.run_dir(run_id)
        return self._contained(root / "approvals" / f"{approval_id}.json", root)

    def action_path(self, run_id: str, idempotency_key: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", idempotency_key):
            raise LabError("invalid_idempotency_key", idempotency_key)
        root = self.run_dir(run_id)
        return self._contained(root / "actions" / f"{idempotency_key}.json", root)

    def exchange_path(self, run_id: str, name: str) -> Path:
        if "/" in name or "\\" in name or name.startswith("."):
            raise LabError("invalid_exchange_name", name)
        root = self.run_dir(run_id)
        return self._contained(root / "exchange" / name, root)

    def save_state(self, state: dict[str, Any]) -> None:
        atomic_write_json(self.state_path(state["run_id"]), state)

    def load_state(self, run_id: str) -> dict[str, Any]:
        return read_json(self.state_path(run_id))

    def append_trace(self, run_id: str, event_type: str, **details: Any) -> dict[str, Any]:
        events = self.trace(run_id)
        event = {
            "schema_version": SCHEMA_VERSION,
            "kind": "trace_event",
            "event_id": identifier("EVT"),
            "sequence": len(events) + 1,
            "run_id": run_id,
            "event_type": event_type,
            "occurred_at": utc_now(),
            "details": details,
        }
        path = self.trace_path(run_id)
        with open(os_fspath(path), "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def trace(self, run_id: str) -> list[dict[str, Any]]:
        path = self.trace_path(run_id)
        if not path_exists(path):
            return []
        events = [
            json.loads(line)
            for line in read_text(path).splitlines()
            if line.strip()
        ]
        sequences = [event.get("sequence") for event in events]
        if sequences != list(range(1, len(events) + 1)):
            raise LabError("corrupt_trace", f"Sequenza non ricostruibile per {run_id}.")
        return events

    def list_runs(self) -> list[dict[str, Any]]:
        states = []
        with os.scandir(os_fspath(self.runs)) as entries:
            paths = [self.runs / entry.name / "state.json" for entry in entries
                     if RUN_ID_PATTERN.fullmatch(entry.name)]
        for path in sorted(path for path in paths if path_is_file(path)):
            states.append(read_json(path))
        return states
