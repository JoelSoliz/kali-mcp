"""Safe subprocess execution with timeout and structured output."""

from __future__ import annotations

import logging
import shlex
import subprocess
import threading
import traceback
from typing import Any

logger = logging.getLogger(__name__)


class CommandExecutor:
    def __init__(
        self,
        command: list[str],
        timeout: int = 300,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ):
        self.command = command
        self.timeout = timeout
        self.cwd = cwd
        self.env = env
        self.process: subprocess.Popen[str] | None = None
        self.stdout_data = ""
        self.stderr_data = ""
        self.return_code: int | None = None
        self.timed_out = False

    def _read_stdout(self) -> None:
        assert self.process and self.process.stdout
        for line in iter(self.process.stdout.readline, ""):
            self.stdout_data += line

    def _read_stderr(self) -> None:
        assert self.process and self.process.stderr
        for line in iter(self.process.stderr.readline, ""):
            self.stderr_data += line

    def execute(self) -> dict[str, Any]:
        logger.info("Executing: %s", shlex.join(self.command))

        try:
            self.process = subprocess.Popen(
                self.command,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.cwd,
                env=self.env,
            )

            stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            try:
                self.return_code = self.process.wait(timeout=self.timeout)
                stdout_thread.join()
                stderr_thread.join()
            except subprocess.TimeoutExpired:
                self.timed_out = True
                logger.warning("Command timed out after %s seconds", self.timeout)
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.return_code = -1

            success = (
                True
                if self.timed_out and (self.stdout_data or self.stderr_data)
                else self.return_code == 0
            )

            return {
                "command": self.command,
                "stdout": self.stdout_data,
                "stderr": self.stderr_data,
                "return_code": self.return_code,
                "success": success,
                "timed_out": self.timed_out,
                "partial_results": self.timed_out and bool(self.stdout_data or self.stderr_data),
            }

        except Exception as exc:
            logger.error("Execution error: %s", exc)
            logger.debug(traceback.format_exc())
            return {
                "command": self.command,
                "stdout": self.stdout_data,
                "stderr": f"Error executing command: {exc}\n{self.stderr_data}",
                "return_code": -1,
                "success": False,
                "timed_out": False,
                "partial_results": bool(self.stdout_data or self.stderr_data),
            }


def run_command(
    command: list[str],
    timeout: int = 300,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    return CommandExecutor(command, timeout=timeout, cwd=cwd, env=env).execute()
