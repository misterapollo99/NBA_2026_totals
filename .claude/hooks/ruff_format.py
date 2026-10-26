"""PostToolUse hook: format any .py file Claude just edited or wrote with ruff.

Claude Code passes the tool call as JSON on stdin. This hook never blocks:
if ruff is missing or the file is not Python, it exits quietly.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_ruff() -> str | None:
    # Prefer the project venv so the hook works without activating it.
    for candidate in (Path(".venv/Scripts/ruff.exe"), Path(".venv/bin/ruff")):
        if candidate.exists():
            return str(candidate)
    return shutil.which("ruff")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return
    ruff = find_ruff()
    if ruff:
        subprocess.run([ruff, "format", file_path], capture_output=True)


if __name__ == "__main__":
    main()
