# Lily.ai Take-Home Assessment

Technical take-home for a Solutions Engineer role at Lily.ai (AI product attribution for retail).
Two parts: a pandas catalog-merge script and SQL queries against NBA season stats.
Full instructions: `docs/assessment.pdf`.

## Layout

- `data/` inputs: catalog.csv, updates.tsv, color_map.json, and the NBA CSV (`nba_2025_26_totals.csv`, downloaded manually)
- `output/` the three CSVs the Python script writes
- `sql/` SQLite loader, `solutions.sql`, `sql_solutions.md`
- `prompts/` task prompts for each phase
- `update_catalog.py` the Python deliverable (repo root)

## Environment

- Windows, PowerShell. Python venv at `.venv` (`.venv\Scripts\python`).
- SQLite for the SQL part, loaded from Python with the standard `sqlite3` module.
- Formatting and linting: ruff. A hook auto-formats `.py` files after every edit.

## How to work

- Explore and plan first. List ambiguities and proposed assumptions, then wait for approval before writing code.
- Prefer small, named pure functions and a `main()`. No classes, CLI frameworks, or logging setup.
- Comments explain *why*, not *what*. Every assumption goes in the module docstring and later in the README.
- After any change to a deliverable, run `/check-takehome` and report the results.
- Never edit expected values in the acceptance tests to make them pass. If a check fails, explain why first.
- Never invent data or query results. Every number in a doc must come from actually running code.
- Commit after each working milestone with a clear message.

## Writing style for docs and README

Plain, professional, concise. No em dashes. No marketing language.
