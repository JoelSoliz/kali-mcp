"""Introspect installed binaries via man pages and version probes."""

from __future__ import annotations

import logging
import re
import shutil
from typing import Any

from kali_mcp.executor import run_command

logger = logging.getLogger(__name__)

MAN_SECTIONS = ("NAME", "SYNOPSIS", "DESCRIPTION", "OPTIONS", "EXAMPLES", "SEE ALSO")


def binary_exists(binary: str) -> bool:
    return shutil.which(binary) is not None


def binary_path(binary: str) -> str | None:
    return shutil.which(binary)


def fetch_man_page(man_target: str, timeout: int = 30) -> dict[str, Any]:
    """Fetch and parse a man page from the local system."""
    if not binary_exists("man"):
        return {"available": False, "error": "man command not found on this system"}

    result = run_command(["man", "-P", "cat", man_target], timeout=timeout)
    if result["return_code"] != 0 and not result["stdout"]:
        # Some systems use MANWIDTH instead of -P cat
        result = run_command(["man", man_target], timeout=timeout)

    if not result["stdout"]:
        return {
            "available": False,
            "error": result["stderr"] or f"No man page for {man_target}",
            "raw_exit_code": result["return_code"],
        }

    parsed = _parse_man_text(result["stdout"])
    parsed["available"] = True
    parsed["man_target"] = man_target
    return parsed


def probe_version(binary: str, version_flags: list[str] | None = None, timeout: int = 15) -> dict[str, Any]:
    """Try common version flags against a binary."""
    flags = version_flags or ["--version", "-V", "-v", "version"]
    path = binary_path(binary)

    info: dict[str, Any] = {
        "binary": binary,
        "path": path,
        "installed": path is not None,
        "version": None,
        "version_output": None,
        "probe_flag": None,
    }

    if not path:
        return info

    for flag in flags:
        command = [binary, flag] if flag != "version" else [binary, "version"]
        result = run_command(command, timeout=timeout)
        output = (result["stdout"] or result["stderr"]).strip()
        if output and result["return_code"] in (0, 1):
            info["version"] = _extract_version(output)
            info["version_output"] = output
            info["probe_flag"] = flag
            break

    return info


def build_tool_metadata(
    binary: str,
    man_page: str | None = None,
    version_flags: list[str] | None = None,
    use_man: bool = True,
    use_version: bool = True,
    timeout: int = 30,
) -> dict[str, Any]:
    """Aggregate runtime metadata for a configured tool."""
    man_target = man_page or binary
    metadata: dict[str, Any] = {
        "binary": binary,
        "path": binary_path(binary),
        "installed": binary_exists(binary),
    }

    if use_version:
        metadata["version_info"] = probe_version(binary, version_flags, timeout=min(timeout, 15))

    if use_man:
        metadata["man"] = fetch_man_page(man_target, timeout=timeout)

    return metadata


def _parse_man_text(text: str) -> dict[str, Any]:
    sections: dict[str, str] = {}
    current = "_PREAMBLE"
    buffer: list[str] = []

    for line in text.splitlines():
        if _is_section_header(line):
            if buffer:
                sections[current] = "\n".join(buffer).strip()
            current = line.strip().upper()
            buffer = []
        else:
            buffer.append(line.rstrip())

    if buffer:
        sections[current] = "\n".join(buffer).strip()

    name = sections.get("NAME", sections.get("_PREAMBLE", ""))
    synopsis = sections.get("SYNOPSIS", "")
    description = sections.get("DESCRIPTION", "")
    options = sections.get("OPTIONS", "")

    return {
        "name": _first_line(name),
        "synopsis": synopsis,
        "description": _first_paragraph(description),
        "options_summary": _summarize_options(options),
        "sections": {k: v for k, v in sections.items() if k != "_PREAMBLE"},
    }


def _is_section_header(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return False
    return stripped.upper() in MAN_SECTIONS or stripped.isupper()


def _first_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def _first_paragraph(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs[0] if paragraphs else text.strip()


def _summarize_options(options_text: str, limit: int = 12) -> list[dict[str, str]]:
    """Extract short option entries from the OPTIONS section."""
    entries: list[dict[str, str]] = []
    for line in options_text.splitlines():
        match = re.match(r"^\s*(-[\w?-]+(?:,\s*--[\w-]+)?|--[\w-]+)\s+(.*)$", line)
        if match:
            entries.append({"flag": match.group(1).strip(), "description": match.group(2).strip()[:200]})
        if len(entries) >= limit:
            break
    return entries


def _extract_version(output: str) -> str | None:
    patterns = [
        r"(\d+\.\d+\.\d+(?:[-+][\w.]+)?)",
        r"version\s+(\S+)",
        r"v(\d+\.\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
    first_line = output.splitlines()[0].strip() if output else None
    return first_line
