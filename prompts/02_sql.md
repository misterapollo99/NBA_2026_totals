# Prompt 2: SQL on NBA stats

Before starting: download the 2025-26 Season Totals CSV from Basketball Reference ("Share & more" then "Get as Excel/CSV") and save it as data/nba_2025_26_totals.csv.

Start a fresh Claude Code session in plan mode, then paste everything below the line.

---

<context>
SQL part of the same take-home (see docs/assessment.pdf). The dataset is data/nba_2025_26_totals.csv, the 2025-26 NBA Season Totals from Basketball Reference. I'm using SQLite, loaded from Python, so both parts live in one environment. I will need to explain every query in an interview. Conventions are in CLAUDE.md.
</context>

<instructions>
Phase 1: Inspect and plan. Stop for my approval after this.
- Read the CSV and report: column names, row count, non-player rows (for example "League Average"), how traded players appear (combined 2TM/3TM rows plus per-team rows), the player ID column, and blanks in percentage columns.
- Propose a cleaning plan and a decision for each ambiguity below.

Phase 2: Load
- Write sql/load_nba.py. Clean column names (lowercase, underscores, no special characters; FG% becomes fg_pct, 3P becomes fg3, 3PA becomes fg3a, Team becomes team), drop non-player rows, convert percentages to REAL, and write table player_stats to sql/nba.db.
- Create a view player_season with exactly one row per player: the combined row for traded players, the single row otherwise. Explain this in a comment.

Phase 3: Queries
Write all 10 queries in sql/solutions.sql, each preceded by a comment with the question number, question text, and a one-line note on logic and assumptions.
- Player-level questions (1, 2, 3, 4, 5, 7, 8, 10) use player_season.
- Team-level questions (6, 9) use player_stats and exclude 2TM/3TM rows.
- Count distinct players by player ID, not name.
- Q7: PPG = CAST(pts AS REAL) / g. State whether you average player PPGs or compute SUM(pts)/SUM(g) per position, and apply a stated minimum-games filter.
- Q8: league average FG% = SUM(fg)/SUM(fga), not AVG(fg_pct). Apply a stated minimum FGA threshold.
- Q9: use RANK() and say why over DENSE_RANK().
- Q10: must use a CTE.
- Watch SQLite integer division; cast where needed.

Phase 4: Run and document
- Run every query against sql/nba.db and generate sql/sql_solutions.md with, for each question: the query in a code block, the result (top 10 to 15 rows for long results, with total row count), and the logic note.
- Header: engine (SQLite and version), dataset (season, source, download date), and data-cleaning decisions.
- Invoke /check-takehome to sanity-check the database. Flag anything that looks off rather than silently adjusting.
</instructions>

<constraints>
- Do not invent data or results. Every result in the doc must come from running the query.
- Readable SQL: consistent aliasing, one clause per line, no unnecessary subqueries.
- Commit after the loader works and again after the doc is generated.
</constraints>
