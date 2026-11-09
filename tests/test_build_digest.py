import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_digest as bd  # noqa: E402

TODAY = date(2026, 11, 5)
FRONTMATTER_NOTE = "---\ntitle: From frontmatter\nowner: Dan\n---\n\n# Real heading\n\nBody.\n"


def git(brain, *args, author="Ann", when="2026-11-05T12:00:00"):
    env = dict(os.environ, GIT_AUTHOR_NAME=author, GIT_AUTHOR_EMAIL=f"{author}@x",
               GIT_COMMITTER_NAME=author, GIT_COMMITTER_EMAIL=f"{author}@x",
               GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    subprocess.run(["git", *args], cwd=brain, env=env, check=True, capture_output=True)


def write(brain, rel, text):
    path = brain / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(brain, rel, text, author, when):
    write(brain, rel, text)
    git(brain, "add", rel, author=author, when=when)
    git(brain, "commit", "-m", f"edit {rel}", author=author, when=when)


def make_brain(tmp_path):
    git(tmp_path, "init", "-q")
    return tmp_path


# Bug 1: the title was the first line of the file, so frontmatter gave "---".
def test_title_is_first_heading_not_frontmatter():
    assert bd.get_title(FRONTMATTER_NOTE, Path("notes/a.md")) == "Real heading"


def test_title_falls_back_to_file_name_without_heading():
    assert bd.get_title("Owner: Dan, status: draft\n\nBody.\n", Path("notes/a.md")) == "a"


# Bug 2: every note got the date and author of the repo's latest commit,
# so every note looked New, dated the day the digest was built.
def test_dates_and_authors_come_from_each_notes_own_history(tmp_path):
    brain = make_brain(tmp_path)
    commit(brain, "old.md", "# Old\n", "Ann", "2026-10-01T12:00:00")
    commit(brain, "old.md", "# Old\n\nEdited.\n", "Bob", "2026-11-04T12:00:00")
    commit(brain, "fresh.md", "# Fresh\n", "Cat", "2026-11-03T12:00:00")
    commit(brain, "other.txt", "not a note", "Dan", "2026-11-05T12:00:00")

    new, updated, _, _ = bd.build_digest(brain, 7, TODAY)

    assert [(r["file"], r["date"], r["who"]) for r in new] == [("fresh.md", "2026-11-03", "Cat")]
    assert [(r["file"], r["date"], r["who"]) for r in updated] == [("old.md", "2026-11-04", "Bob")]


# Bug 3: hidden folders are already filtered out, so folders[0] was a real
# folder (in the brain: 01-why), not .git, and its notes were never scanned.
def test_notes_in_the_first_folder_are_found(tmp_path):
    brain = make_brain(tmp_path)
    write(brain, "01-why/why.md", "# Why\n")
    write(brain, "02-market/market.md", "# Market\n")

    assert [p.as_posix() for p in bd.find_notes(brain)] == ["01-why/why.md", "02-market/market.md"]


# Bug 4: a note with no commit crashed get_history, the crash was swallowed,
# and the note vanished instead of showing under "Not committed yet".
def test_note_without_commit_is_listed_as_not_committed(tmp_path):
    brain = make_brain(tmp_path)
    commit(brain, "done.md", "# Done\n", "Ann", "2026-11-04T12:00:00")
    write(brain, "draft.md", "# Draft\n")

    new, _, uncommitted, problems = bd.build_digest(brain, 7, TODAY)

    assert [r["file"] for r in new] == ["done.md"]
    assert [(r["file"], r["title"]) for r in uncommitted] == [("draft.md", "Draft")]
    assert problems == []


# Bug 5: a note that couldn't be read was dropped silently;
# README says it goes under "Could not read".
def test_unreadable_note_is_reported_and_the_rest_still_build(tmp_path):
    brain = make_brain(tmp_path)
    commit(brain, "good.md", "# Good\n", "Ann", "2026-11-04T12:00:00")
    (brain / "bad.md").write_bytes(b"# Bad \xff\xfe\n")

    new, _, _, problems = bd.build_digest(brain, 7, TODAY)

    assert [r["file"] for r in new] == ["good.md"]
    assert problems == ["bad.md"]


# Bug 6: the header counted every path in git log (.gitkeep files, moved-away
# paths, non-notes) instead of the New and Updated notes shown in the tables.
def test_header_counts_match_the_tables(tmp_path):
    brain = make_brain(tmp_path)
    today = date.today().isoformat()
    commit(brain, "note.md", "# Note\n", "Ann", f"{today}T00:00:01")
    commit(brain, "empty/.gitkeep", "", "Ann", f"{today}T00:00:01")
    commit(brain, "other.txt", "not a note", "Ann", f"{today}T00:00:01")

    script = Path(bd.__file__)
    subprocess.run([sys.executable, str(script), "--brain", str(brain)], check=True, capture_output=True)
    header = (brain / "DIGEST.md").read_text(encoding="utf-8").splitlines()[2]

    assert header.startswith("Last 7 days: 1 new, 0 updated.")
