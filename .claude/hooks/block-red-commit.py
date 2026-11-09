#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block `git commit` while the test suite is red.

Claude Code sends the tool call as JSON on stdin. Exit 2 blocks the call and
shows stderr to Claude; exit 0 lets it through.
"""
import json
import os
import subprocess
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if "git commit" not in command:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=project_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("Blocked: tests are red", file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
