# brain-digest

Builds `DIGEST.md` in your brain repo: what is new and what was updated in the last few days, so the team can catch up in a minute.

Written by Dan Reyes (ops). Dan has left the team.

## Run it

```
python build_digest.py --brain path/to/your/brain
```

Looks back 7 days by default. To look further: `--days 14`.

Python 3.10+ and git. No other installs.

## What counts as a note

- Every `.md` file in the brain, in any folder, at any depth.
- Except `README.md`, `CLAUDE.md` and `DIGEST.md` in the root of the brain.
- Except anything inside `archive/`. Archived notes are out of date on purpose and must stay out of the digest.
- Except anything inside `.claude/` and `.github/`. Skills, agents and workflows are not notes.

## What goes in the digest

- **The window** is the last 7 days (or `--days`), including today.
- **New:** notes whose first commit is inside the window. Shows the day it was created and who created it.
- **Updated:** notes created before the window and changed inside it. Shows the day of the latest change and who made it.
- A note appears once: if it was created and then edited inside the window, it is New.
- Notes created before the window and not changed since are not in the digest. That is on purpose.
- **Not committed yet:** notes that exist in the folder but have no commit. Listed at the bottom so nobody forgets them.
- Both tables are sorted newest first.

## Columns

| Column | What it shows |
|---|---|
| Date | `YYYY-MM-DD`, see the rules above |
| Title | The first `# ` heading in the note. The note's header (frontmatter, or an owner / date / status line) is not a title. No heading: the file name |
| Topic | The top folder the note sits in. Notes in the root: `general` |
| Created by / Updated by | Commit author, see the rules above |
| File | Path inside the brain |

The line under the heading says how many notes are New and how many are Updated. Those numbers match the tables.

