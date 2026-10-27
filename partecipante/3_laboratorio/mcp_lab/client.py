"""Host demo with a real stdio MCP client/server exchange. Standard library only."""
import argparse
import json
import subprocess
import sys
import threading
import queue
import time
from pathlib import Path


def run_demo(output, run_id):
    server = subprocess.Popen([sys.executable, "-u", str(Path(__file__).with_name("server.py"))], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    incoming = queue.Queue()
    threading.Thread(target=lambda: [incoming.put(line) for line in server.stdout], daemon=True).start()
    trace = []
    sequence = 0
    def exchange(method, params=None, notification=False):
        nonlocal sequence
        sequence += 1
        message = {"jsonrpc": "2.0", "method": method}
        if not notification:
            message["id"] = sequence
        if params is not None:
            message["params"] = params
        trace.append({"direction": "client_to_server", "message": message})
        server.stdin.write(json.dumps(message) + "\n")
        server.stdin.flush()
        if notification:
            return None
        response = json.loads(incoming.get(timeout=5))
        if response.get("id") != sequence or response.get("jsonrpc") != "2.0":
            raise RuntimeError("Mismatched response")
        trace.append({"direction": "server_to_client", "message": response})
        return response
    started = time.perf_counter()
    try:
        initialization = exchange("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "meridiano-host", "version": "1.0"}})
        if initialization["result"]["protocolVersion"] != "2025-06-18":
            raise RuntimeError("Unsupported protocol version")
        exchange("notifications/initialized", notification=True)
        listed = exchange("tools/list")
        if listed["result"]["tools"][0]["name"] != "lookup_synthetic_source":
            raise RuntimeError("Tool unavailable")
        success = exchange("tools/call", {"name": "lookup_synthetic_source", "arguments": {"record_id": "MER-VARIANT-01"}})
        missing = exchange("tools/call", {"name": "lookup_synthetic_source", "arguments": {"record_id": "MISSING"}})
        invalid = exchange("tools/call", {"name": "publish", "arguments": {}})
        assert success["result"]["isError"] is False
        assert missing["result"]["isError"] is True
        assert invalid["error"]["code"] == -32602
        report = {"run_id": run_id, "transport": "stdio_real_subprocess", "protocol_version": "2025-06-18", "model_used": False, "elapsed_seconds": round(time.perf_counter()-started, 3), "status": "PASS_LOCAL_MCP", "source_error_behavior": "STOP_NO_EVIDENCE_NO_APPROVAL", "approval": "HUMAN_REQUIRED", "effects": "NOT_SENT", "trace": trace}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return report
    finally:
        server.stdin.close()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=3)
        server.stdout.close()
        server.stderr.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("reports/mcp_trace.json"))
    parser.add_argument("--run-id", required=True, help="Existing baseline run ID or explicit demo ID")
    args = parser.parse_args()
    report = run_demo(args.out, args.run_id)
    print(report["status"], args.out, "source error -> stop; no approval")
