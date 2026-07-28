"""One command runner for all external media and graphics tools."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from video_engine.errors import ExternalToolError


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
        }


class CommandRunner:
    def __init__(self, *, default_timeout: float | None = None) -> None:
        self.default_timeout = default_timeout

    def run(
        self,
        command: Sequence[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check: bool = True,
        input_text: str | None = None,
    ) -> CommandResult:
        normalized = tuple(os.fspath(part) for part in command)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                normalized,
                cwd=cwd,
                env={**os.environ, **dict(env or {})},
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout if timeout is not None else self.default_timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ExternalToolError(
                "external executable was not found",
                context={"executable": normalized[0], "command": list(normalized)},
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ExternalToolError(
                "external command timed out",
                context={
                    "command": list(normalized),
                    "timeout_seconds": timeout if timeout is not None else self.default_timeout,
                },
            ) from exc
        result = CommandResult(
            command=normalized,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
        )
        if check and result.return_code != 0:
            raise ExternalToolError(
                "external command failed",
                context={
                    "command": list(normalized),
                    "return_code": result.return_code,
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                },
            )
        return result
