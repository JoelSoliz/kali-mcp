"""Discover installed Kali tools and build MCP JSON configuration."""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from typing import Any, Iterable

from kali_mcp.catalog import (
    CATEGORY_KEYWORDS,
    KALI_TOOL_CATALOG,
    TOOL_FIXED_ARGS,
    TOOL_PARAMETER_TEMPLATES,
    TARGET_FLAG_HINTS,
    CatalogEntry,
)
from kali_mcp.executor import run_command
from kali_mcp.introspection import fetch_man_page, probe_version
from kali_mcp.schema import ParameterDef, ServerConfig, ToolDef, parse_config

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredTool:
    binary: str
    path: str
    category: str
    description: str
    man_page: str | None
    version: str | None
    man_available: bool
    source: str


def discover_installed_tools(
    categories: Iterable[str] | None = None,
    include_dpkg: bool = True,
    include_man_scan: bool = False,
    man_scan_limit: int = 30,
) -> list[DiscoveredTool]:
    """Detect installed tools on the current host (intended for Kali Linux)."""
    allowed_categories = {c.lower() for c in categories} if categories else None
    found: dict[str, DiscoveredTool] = {}

    for entry in KALI_TOOL_CATALOG:
        if allowed_categories and entry.category.lower() not in allowed_categories:
            continue
        path = shutil.which(entry.binary)
        if not path:
            continue
        discovered = _build_discovered_tool(entry, path, source="catalog")
        found[entry.binary] = discovered

    if include_dpkg:
        for binary in _discover_from_dpkg():
            if binary in found:
                continue
            path = shutil.which(binary)
            if not path:
                continue
            entry = CatalogEntry(binary, _guess_category(binary), description=f"Installed tool: {binary}")
            found[binary] = _build_discovered_tool(entry, path, source="dpkg")

    if include_man_scan:
        for binary in _discover_from_man_keywords(limit=man_scan_limit):
            if binary in found:
                continue
            path = shutil.which(binary)
            if not path:
                continue
            entry = CatalogEntry(binary, _guess_category(binary), description=f"Discovered via man -k: {binary}")
            found[binary] = _build_discovered_tool(entry, path, source="man-k")

    return sorted(found.values(), key=lambda item: (item.category, item.binary))


def build_config_from_discovery(
    discovered: list[DiscoveredTool],
    server_name: str = "kali-mcp",
    server_version: str = "0.1.0",
    merge_with: ServerConfig | None = None,
) -> ServerConfig:
    """Convert discovered tools into a ServerConfig, optionally merging with an existing config."""
    if merge_with:
        config = ServerConfig(
            name=merge_with.name,
            version=merge_with.version,
            description=merge_with.description,
            defaults=merge_with.defaults,
            tools=list(merge_with.tools),
        )
        existing_binaries = {tool.binary for tool in config.tools}
        existing_names = {tool.name for tool in config.tools}
    else:
        config = ServerConfig(name=server_name, version=server_version)
        existing_binaries = set()
        existing_names = set()

    for item in discovered:
        if item.binary in existing_binaries:
            continue
        tool_def = _discovered_to_tool_def(item, existing_names)
        config.tools.append(tool_def)
        existing_binaries.add(item.binary)
        existing_names.add(tool_def.name)

    return config


def _build_discovered_tool(entry: CatalogEntry, path: str, source: str) -> DiscoveredTool:
    man_target = entry.man_page or entry.binary
    man = fetch_man_page(man_target, timeout=20)
    version_info = probe_version(entry.binary, entry.version_flags, timeout=10)

    description = entry.description
    if man.get("available"):
        man_desc = man.get("description") or man.get("name")
        if man_desc:
            description = _truncate(man_desc, 240)

    return DiscoveredTool(
        binary=entry.binary,
        path=path,
        category=entry.category,
        description=description,
        man_page=man_target if man.get("available") else None,
        version=version_info.get("version"),
        man_available=bool(man.get("available")),
        source=source,
    )


def _discovered_to_tool_def(item: DiscoveredTool, used_names: set[str]) -> ToolDef:
    template = TOOL_PARAMETER_TEMPLATES.get(item.binary)
    if template:
        parameters = [_template_param(raw) for raw in template]
    else:
        parameters = _parameters_from_man(item)

    tool_name = _unique_tool_name(item.binary, used_names)
    return ToolDef(
        name=tool_name,
        binary=item.binary,
        category=item.category,
        description=item.description,
        man_page=item.man_page,
        parameters=parameters,
        fixed_args=TOOL_FIXED_ARGS.get(item.binary, []),
        allow_additional_args=True,
    )


def _template_param(raw: dict[str, Any]) -> ParameterDef:
    return ParameterDef(
        name=raw["name"],
        description=raw.get("description", ""),
        type=raw.get("type", "string"),
        required=raw.get("required", False),
        default=raw.get("default"),
        arg_style=raw.get("argStyle", "kv"),
        flag=raw.get("flag"),
        position=raw.get("position"),
    )


def _parameters_from_man(item: DiscoveredTool) -> list[ParameterDef]:
    """Build a minimal generic parameter set using man page hints."""
    if not item.man_available:
        return [
            ParameterDef(
                name="target",
                description="Primary target (host, URL, file, or path)",
                type="string",
                required=True,
                arg_style="positional",
                position=99,
            )
        ]

    man = fetch_man_page(item.man_page or item.binary, timeout=20)
    options = man.get("options_summary", [])
    parameters: list[ParameterDef] = []

    for option in options:
        flag = option["flag"].split(",")[0].strip()
        if flag in TARGET_FLAG_HINTS:
            parameters.append(
                ParameterDef(
                    name=_flag_to_param_name(flag),
                    description=_truncate(option.get("description", ""), 180) or "Target parameter",
                    type="string",
                    required=True,
                    arg_style="kv",
                    flag=flag,
                )
            )
            break

    if not parameters:
        parameters.append(
            ParameterDef(
                name="target",
                description="Primary target inferred from tool synopsis",
                type="string",
                required=True,
                arg_style="positional",
                position=99,
            )
        )

    return parameters


def _discover_from_dpkg() -> list[str]:
    if not shutil.which("dpkg-query"):
        return []

    patterns = [
        "nmap",
        "nikto",
        "wpscan",
        "gobuster",
        "dirb",
        "ffuf",
        "sqlmap",
        "hydra",
        "john",
        "hashcat",
        "metasploit",
        "aircrack",
        "wireshark",
        "responder",
        "impacket",
        "enum4linux",
        "whatweb",
        "sslscan",
        "theharvester",
        "recon-ng",
        "commix",
        "wfuzz",
        "binwalk",
        "foremost",
        "steghide",
        "kali-linux",
    ]

    discovered: set[str] = set()
    for pattern in patterns:
        result = run_command(
            ["dpkg-query", "-W", "-f=${Package}\n", f"{pattern}*"],
            timeout=30,
        )
        if result["return_code"] != 0:
            continue
        for package in result["stdout"].splitlines():
            package = package.strip()
            if not package:
                continue
            binaries = _binaries_from_package(package)
            discovered.update(binaries)

    return sorted(discovered)


def _binaries_from_package(package: str) -> list[str]:
    result = run_command(["dpkg-query", "-L", package], timeout=30)
    if result["return_code"] != 0:
        return []

    binaries: list[str] = []
    for line in result["stdout"].splitlines():
        path = line.strip()
        if not path.startswith(("/usr/bin/", "/usr/sbin/", "/bin/", "/sbin/")):
            continue
        name = path.rsplit("/", 1)[-1]
        if _looks_like_cli(name):
            binaries.append(name)
    return binaries


def _discover_from_man_keywords(limit: int = 30) -> list[str]:
    if not shutil.which("man"):
        return []

    keywords = ("security", "scanner", "exploit", "password", "network", "vulnerability")
    discovered: list[str] = []
    seen: set[str] = set()

    for keyword in keywords:
        result = run_command(["man", "-k", keyword], timeout=20)
        if result["return_code"] != 0:
            continue
        for line in result["stdout"].splitlines():
            match = re.match(r"^(\S+)", line)
            if not match:
                continue
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            if shutil.which(name) and _looks_like_cli(name):
                discovered.append(name)
            if len(discovered) >= limit:
                return discovered

    return discovered


def _guess_category(binary: str) -> str:
    man = fetch_man_page(binary, timeout=10)
    haystack = " ".join(
        [
            binary,
            man.get("name", ""),
            man.get("description", ""),
            man.get("synopsis", ""),
        ]
    ).lower()

    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for keyword in keywords if keyword in haystack)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _unique_tool_name(binary: str, used_names: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", binary.lower()).strip("_") or "tool"
    if not base[0].isalpha():
        base = f"tool_{base}"
    candidate = f"{base}_run"
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}_run_{suffix}"
        suffix += 1
    return candidate


def _flag_to_param_name(flag: str) -> str:
    cleaned = flag.lstrip("-").replace("-", "_")
    mapping = {"h": "target", "u": "url", "url": "url", "host": "host", "t": "target"}
    return mapping.get(cleaned, cleaned or "target")


def _looks_like_cli(name: str) -> bool:
    if not name or name.startswith("."):
        return False
    blocked = {
        "sh",
        "bash",
        "dash",
        "python",
        "python3",
        "perl",
        "sed",
        "awk",
        "grep",
        "ls",
        "cat",
        "cp",
        "mv",
        "rm",
        "mkdir",
        "chmod",
        "chown",
        "systemctl",
        "service",
        "dpkg",
        "apt",
        "apt-get",
    }
    return name not in blocked and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._+-]*", name) is not None


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
