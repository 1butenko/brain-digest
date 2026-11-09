#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block `git commit` while the test suite is red.

Claude Code sends the tool call (Bash or PowerShell) as JSON on stdin. Exit 2
blocks the call and shows stderr to Claude; exit 0 lets it through.
"""
import json
import os
import re
import subprocess
import sys

# `git ... commit` where git starts a command: at the start, or after ; & | ( { or a newline.
# Allows env assignments before git and global options between git and commit
# (`git -c user.email=x commit`, `git -C "some dir" commit`, `git --no-pager commit`).
# Text that only mentions it (`echo 'git commit'`, `grep "git commit"`) doesn't match.
_ARG = r"""(?:"[^"]*"|'[^']*'|\S+)"""
COMMIT_RE = re.compile(
    r"(?:^|[;&|({\n]|\$\()\s*"                    # start of a command
    r"(?:[A-Za-z_]\w*=" + _ARG + r"\s+)*"          # FOO=bar env assignments
    r"(?:\S*[/\\])?git(?:\.exe)?"                 # git, /usr/bin/git, git.exe
    r"(?:\s+(?:-[cC]\s+" + _ARG + r"|--?[\w-]+(?:=" + _ARG + r")?))*"  # global options
    r"\s+commit(?![\w-])"                          # commit, not commit-tree
)


def is_commit(command):
    return bool(COMMIT_RE.search(command))


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if not is_commit(command):
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
