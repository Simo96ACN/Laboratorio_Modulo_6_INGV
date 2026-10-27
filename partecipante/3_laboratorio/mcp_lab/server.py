"""Minimal local MCP server, pinned protocol 2025-06-18; stdio only.
Educational subset: initialize, ping, tools/list and tools/call. No LLM here.
"""
import json
import sys
from pathlib import Path

VERSION = "2025-06-18"
SOURCE = Path(__file__).with_name("source.json")
TOOL = {"name": "lookup_synthetic_source", "description": "Read a synthetic Meridiano evidence record, never authorize publication.",
        "inputSchema": {"type": "object", "properties": {"record_id": {"type": "string"}}, "required": ["record_id"], "additionalProperties": False}}


def serve():
    initialized = False
    negotiated = False
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), flush=True)
            continue
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        result = None
        error = None
        if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
            error = {"code": -32600, "message": "Invalid Request"}
        elif method == "notifications/initialized":
            initialized = negotiated
            continue
        elif method == "initialize":
            negotiated = True
            result = {"protocolVersion": VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "meridiano-local-source", "version": "1.0"}}
        elif method == "ping":
            result = {}
        elif not initialized:
            error = {"code": -32002, "message": "Initialize first"}
        elif method == "tools/list":
            result = {"tools": [TOOL]}
        elif method == "tools/call":
            arguments = params.get("arguments", {})
            if params.get("name") != TOOL["name"]:
                error = {"code": -32602, "message": "Unknown tool"}
            elif set(arguments) != {"record_id"} or not isinstance(arguments["record_id"], str):
                error = {"code": -32602, "message": "record_id string required; no other arguments"}
            else:
                records = json.loads(SOURCE.read_text(encoding="utf-8"))
                record = records.get(arguments["record_id"])
                result = {"content": [{"type": "text", "text": json.dumps(record if record else {"code": "SOURCE_NOT_FOUND", "record_id": arguments["record_id"]}, ensure_ascii=False)}], "isError": record is None}
        else:
            error = {"code": -32601, "message": "Method not found"}
        if "id" in request:
            response = {"jsonrpc": "2.0", "id": request_id}
            response["error" if error else "result"] = error or result
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    serve()
