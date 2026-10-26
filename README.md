# Lily.ai take-home

**Part 1** merges catalog updates, normalizes colors, and adjusts prices. **Part 2** answers 10 SQL questions about 2025-26 NBA season totals.

| Path | Contents |
|---|---|
| `update_catalog.py` | Part 1 script. Reads `data/catalog.csv`, `updates.tsv`, `color_map.json`; writes `output/` |
| `output/` | Part 1 deliverables: `updated_catalog.csv`, `product_detail_only.csv`, `colors_summary.csv` |
| `tests/` | pytest suite for Part 1 |
| `sql/load_nba.py` | Loads `data/nba_2025_26_totals.csv` into `sql/nba.db` (table `player_stats`, view `player_season`) |
| `sql/solutions.sql` | The 10 queries, each with a logic note |
| `sql/validation.sql` | Reconciliation, tie, and sensitivity checks |
| `sql/build_report.py` | Reloads the db, runs both .sql files, writes `sql/sql_solutions.md` and `sql/results/*.csv` |
| `sql/sql_solutions.md` | Submitted answers: queries, results, notes, validation, flags |

## How to run (PowerShell, from a fresh clone)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python update_catalog.py
.\.venv\Scripts\python sql\build_report.py
.\.venv\Scripts\python -m pytest -q
```

Run everything from the repo root. `build_report.py` runs the loader first, so there is no separate load step.

## Versions

Python 3.12.10, SQLite 3.49.1 (bundled with Python's `sqlite3`), pandas 3.1.0, pytest 9.1.1, ruff 0.17.2. Exact pins are in `requirements.lock.txt`.

`sql/solutions.sql` runs on its own against any `player_stats` table on SQLite 3.25 or later (the first release with window functions, which Q6 and Q9 need). `sql/validation.sql` and the report build use `GROUP_CONCAT(... ORDER BY ...)`, so they need SQLite 3.44 or later. Check yours with `.\.venv\Scripts\python -c "import sqlite3; print(sqlite3.sqlite_version)"`.

## Assumptions and decisions

**Part 1** (the full list is in the `update_catalog.py` docstring)
- All fields are read as text, so ids like `0042` stay as they are. Updates are left-joined by id; duplicate ids in either file are an error.
- Color tokens are split on commas, trimmed, and lowercased. Additions are applied before removals, and removals match the raw token before it is mapped to a canonical color. Unmapped tokens fall back to title case and are reported.
- `price_adjust` must be a percentage with `%`. Prices use Decimal with half-up rounding and two decimals. An unparseable or negative result is an error naming the SKU.
- `color_list` keeps the original input; normalized colors are in `product_detail`.

**Part 2** (details and numbers are in `sql/sql_solutions.md`)
- `player_id` (Basketball Reference's Player-additional) is the player key. The League Average row is moved to table `league_average` and used only to reconcile results.
- A blank percentage means zero attempts and is stored as NULL, not 0.
- Player-level questions use `player_season`: one row per player, using the combined 2TM/3TM row for traded players. Team-level questions (Q6, Q9) use per-team rows only.
- Q7 averages player PPG by position with a 20-game minimum. Q8 uses league FG% = SUM(fg)/SUM(fga) and a 300-FGA minimum. Q10 counts players with no 3-point attempts in the average. The validation section shows the results without these choices; PG leads Q7 under every variant.
- Q6 and Q9 use `RANK()` so tied players share a rank and none are dropped.

## How this was built

Built with Claude Code. `CLAUDE.md` and `.claude/` hold the project conventions, tool permissions, a hook that runs ruff format after each edit, and the `check-takehome` skill. That skill's acceptance values were written before any code. `prompts/` holds the prompts used for each part.
