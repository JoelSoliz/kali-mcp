"""Append-only JSONL audit log for MCP tool executions."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "tool-calls.jsonl"

_execution_context: ContextVar[dict[str, Any]] = ContextVar("execution_context", default={})


def set_execution_context(**context: Any) -> None:
    """Attach metadata (source, client_ip) for the current tool execution."""
    current = dict(_execution_context.get())
    current.update(context)
    _execution_context.set(current)


def get_execution_context() -> dict[str, Any]:
    return dict(_execution_context.get())


def default_log_path() -> Path:
    return DEFAULT_LOG_FILE


class ToolCallLogger:
    """Thread-safe JSONL logger for tool invocations."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = (log_path or default_log_path()).expanduser().resolve()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_tool_call(
        self,
        *,
        tool: str,
        binary: str,
        parameters: dict[str, Any],
        command: list[str] | None,
        result: dict[str, Any],
        duration_ms: float,
        error: str | None = None,
    ) -> str:
        context = get_execution_context()
        call_id = uuid.uuid4().hex
        entry: dict[str, Any] = {
            "call_id": call_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": context.get("source", "local"),
            "tool": tool,
            "binary": binary,
            "parameters": parameters,
            "command": command,
            "timeout_seconds": result.get("timeout_seconds"),
            "duration_ms": round(duration_ms, 2),
            "success": result.get("success"),
            "return_code": result.get("return_code"),
            "timed_out": result.get("timed_out", False),
            "partial_results": result.get("partial_results", False),
            "stdout_bytes": len(result.get("stdout") or ""),
            "stderr_bytes": len(result.get("stderr") or ""),
            "error": error or result.get("error"),
        }
        if context.get("client_ip"):
            entry["client_ip"] = context["client_ip"]

        line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

        logger.debug("Tool call logged: %s (%s)", call_id, tool)
        return call_id


_instance: ToolCallLogger | None = None


def configure_tool_call_logger(log_path: Path | str | None = None) -> ToolCallLogger:
    global _instance
    path = Path(log_path).expanduser().resolve() if log_path else default_log_path()
    _instance = ToolCallLogger(path)
    logger.info("Tool call audit log: %s", _instance.log_path)
    return _instance


def get_tool_call_logger() -> ToolCallLogger:
    global _instance
    if _instance is None:
        _instance = ToolCallLogger()
        logger.info("Tool call audit log (default): %s", _instance.log_path)
    return _instance
