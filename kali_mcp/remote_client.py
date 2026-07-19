"""HTTP client for the Kali API server (Windows MCP -> Kali bridge)."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300


class KaliApiClient:
    def __init__(self, server_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        logger.info("Kali API client targeting %s", self.server_url)

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.server_url}{path}"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("GET %s failed: %s", url, exc)
            return {"success": False, "error": str(exc)}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.server_url}{path}"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 404:
                body = self._safe_json(response)
                detail = body.get("error") if isinstance(body, dict) else response.text
                return {
                    "success": False,
                    "error": detail or f"404 Not Found: {url}",
                    "status_code": 404,
                }
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("POST %s failed: %s", url, exc)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def list_tools(self) -> dict[str, Any]:
        return self._get("/api/tools")

    def get_tool_metadata(self, tool_name: str) -> dict[str, Any]:
        return self._get(f"/api/tools/{tool_name}")

    def get_config(self) -> dict[str, Any]:
        return self._get("/api/config")

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/api/tools/{tool_name}/execute", {"arguments": arguments})

    def reload_metadata(self, tool_name: str = "") -> dict[str, Any]:
        payload = {"tool_name": tool_name} if tool_name else {}
        return self._post("/api/tools/metadata/reload", payload)

    def discover_config(
        self,
        categories: list[str] | None = None,
        include_dpkg: bool = True,
        include_man_scan: bool = False,
        merge_with_config: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "includeDpkg": include_dpkg,
            "includeManScan": include_man_scan,
            "mergeWithConfig": merge_with_config,
        }
        if categories:
            payload["categories"] = categories
        return self._post("/api/config/discover", payload)
