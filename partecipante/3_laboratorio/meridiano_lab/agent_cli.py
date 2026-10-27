from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent_session import AgentSession
from .errors import LabError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Tool locali del nodo AI: non esegue import né review.")
    root.add_argument("--workspace", type=Path, required=True)
    root.add_argument("--run-id", required=True)
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("catalog", "request", "status", "check-draft", "submit-draft", "approval-requests"):
        sub.add_parser(command)
    task = sub.add_parser("request-approval")
    task.add_argument("--dataset", required=True)
    task.add_argument("--scope", required=True)
    task.add_argument("--reason", required=True)
    simulate = sub.add_parser("simulate-role-response", help="Gioco di ruolo didattico: il ruolo reale è umano.")
    simulate.add_argument("--task-id", required=True)
    simulate.add_argument("--role", required=True)
    simulate.add_argument("--decision", choices=["APPROVE", "REJECT"], required=True)
    simulate.add_argument("--reason", required=True)
    simulate.add_argument("--model-label", required=True)
    search = sub.add_parser("search-evidence")
    search.add_argument("--dataset", required=True)
    search.add_argument("--query", default="")
    search.add_argument("--cursor")
    read = sub.add_parser("read-evidence")
    selection = read.add_mutually_exclusive_group(required=True)
    selection.add_argument("--evidence-ref", action="append")
    selection.add_argument("--segment", action="append", help="Riferimento@offset; massimo tre segmenti espliciti.")
    read.add_argument("--offset", type=int, default=0)
    need = sub.add_parser("needs-input")
    need.add_argument("--reason", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        # The installed runner constructs the same participant hook/design as manual import.
        import runner
        base = Path(runner.BASE_DIR).resolve()
        workspace = args.workspace.resolve()
        try:
            workspace.relative_to(base)
        except ValueError as exc:
            raise LabError("unsafe_workspace", "Usa un workspace interno al pacchetto estratto.") from exc
        lab = runner.service(args)
        values = vars(args).copy()
        for name in ("workspace", "run_id", "command"):
            values.pop(name)
        result = AgentSession(lab, args.run_id).call(args.command, **values)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except LabError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
