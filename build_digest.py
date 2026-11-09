#!/usr/bin/env python3
"""Build DIGEST.md for a brain repo: what is new and what was updated in the last few days.

Usage:
    python build_digest.py --brain path/to/your/brain
    python build_digest.py --brain path/to/your/brain --days 14

See README.md for the rules.
"""
import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

SKIP_FILES = {"README.md", "CLAUDE.md", "DIGEST.md"}
SKIP_DIRS = {"archive", ".claude", ".github"}


def find_notes(brain):
    """Every .md file in the brain, at any depth, minus the ones README says to skip."""
    notes = [p.relative_to(brain) for p in sorted(brain.glob("*.md")) if p.name not in SKIP_FILES]
    folders = sorted(p for p in brain.iterdir()
                     if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS)
    for folder in folders:  # hidden folders like .git are already left out above
        for path in sorted(folder.rglob("*.md")):
            rel = path.relative_to(brain)
            if any(part in SKIP_DIRS for part in rel.parts[:-1]):
                continue
            notes.append(rel)
    return notes


def get_title(text, rel):
    """The note's first '# ' heading, or the file name if it has none."""
    heading = next((line for line in text.splitlines() if line.startswith("# ")), None)
    return heading[2:].strip() if heading else rel.stem


def get_history(brain, rel):
    """(created_by, created_on, changed_by, changed_on) for one note, or None if it was never committed."""
    result = subprocess.run(
        ["git", "log", "--follow", "--format=%an|%ad", "--date=short", "--", rel.as_posix()],
        cwd=brain, capture_output=True, text=True,
    )
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    changed_by, changed_on = lines[0].split("|", 1)    # newest commit
    created_by, created_on = lines[-1].split("|", 1)   # oldest commit
    return created_by, created_on, changed_by, changed_on


def get_topic(rel):
    return rel.parts[0] if len(rel.parts) > 1 else "general"


def build_digest(brain, days=7, today=None):
    today = today or date.today()
    since = (today - timedelta(days=days - 1)).isoformat()   # "last 7 days" includes today
    new, updated, uncommitted, problems = [], [], [], []
    for rel in find_notes(brain):
        try:
            text = (brain / rel).read_text(encoding="utf-8")
            row = {"file": rel.as_posix(), "title": get_title(text, rel), "topic": get_topic(rel)}
            history = get_history(brain, rel)
            if history is None:
                uncommitted.append(row)
                continue
            created_by, created_on, changed_by, changed_on = history
            if created_on >= since:
                new.append(dict(row, date=created_on, who=created_by))
            elif changed_on >= since:
                updated.append(dict(row, date=changed_on, who=changed_by))
        except Exception:
            problems.append(rel.as_posix())  # one bad note shouldn't stop the whole digest
    new.sort(key=lambda r: r["date"], reverse=True)
    updated.sort(key=lambda r: r["date"], reverse=True)
    return new, updated, uncommitted, problems


def table(rows, who_label):
    out = [f"| Date | Title | Topic | {who_label} | File |", "|---|---|---|---|---|"]
    out += [f"| {r['date']} | {r['title']} | {r['topic']} | {r['who']} | `{r['file']}` |" for r in rows]
    return out


def render(new, updated, uncommitted, problems, days, today):
    out = [
        "# Brain digest",
        "",
        f"Last {days} days: {len(new)} new, {len(updated)} updated. Built {today.isoformat()}.",
        "",
        "## New",
        "",
    ]
    out += table(new, "Created by") if new else ["Nothing new."]
    out += ["", "## Updated", ""]
    out += table(updated, "Updated by") if updated else ["Nothing updated."]
    if uncommitted:
        out += ["", "## Not committed yet", ""] + [f"- {r['title']} (`{r['file']}`)" for r in uncommitted]
    if problems:
        out += ["", "## Could not read", ""] + [f"- {p}" for p in problems]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Build DIGEST.md for a brain repo.")
    parser.add_argument("--brain", required=True, help="path to the brain repo")
    parser.add_argument("--days", type=int, default=7, help="how many days back to look (default 7)")
    args = parser.parse_args()

    brain = Path(args.brain).expanduser().resolve()
    if not brain.is_dir():
        sys.exit(f"Not a folder: {brain}")

    today = date.today()
    new, updated, uncommitted, problems = build_digest(brain, args.days, today)
    (brain / "DIGEST.md").write_text(render(new, updated, uncommitted, problems, args.days, today), encoding="utf-8")
    print(f"Wrote {brain / 'DIGEST.md'}: {len(new)} new, {len(updated)} updated.")
    for p in problems:
        print(f"WARNING: could not read {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
