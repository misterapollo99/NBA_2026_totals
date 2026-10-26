# Prompt 2: SQL on NBA stats

The dataset is already at data/nba_2025_26_totals.csv.

Start a fresh Claude Code session (/clear) in plan mode, then paste everything below the line.

---

<context>
SQL part of the same take-home (see docs/assessment.pdf). The dataset is data/nba_2025_26_totals.csv, the 2025-26 NBA Season Totals from Basketball Reference, downloaded manually. I'm using SQLite, loaded from Python, so both parts of the submission live in one environment. I will need to explain every query in an interview. Conventions are in CLAUDE.md.

What I already know about the file:
- 733 lines, including a final "League Average" row with Player-additional = -9999 and only percentage columns filled.
- Player-additional is the unique player ID. Use it, not the player name, for anything that counts or groups players.
- Traded players appear as a combined row (Team = 2TM, 3TM, etc.) plus one row per team they played for.
- Trp-Dbl and Awards columns exist but aren't needed for any question.
</context>

<instructions>
Phase 1: Inspect and plan. Stop for my approval after this.
- Confirm or correct everything in <context>. Report column names, row count, distinct Team values that represent combined rows, distinct Pos values (including any hybrid positions like "SG-PG"), and blanks or zero-attempt cases in percentage columns.
- Propose a cleaning plan and a specific decision for each ambiguity in Phase 3, including the exact thresholds you'd use for Q7 and Q8 and why.

Phase 2: Load
- Write sql/load_nba.py. Clean column names: lowercase, underscores, no special characters, and never starting with a digit (FG% becomes fg_pct, 3P becomes fg3, 3PA becomes fg3a, 3P% becomes fg3_pct, 2P becomes fg2, eFG% becomes efg_pct, Trp-Dbl becomes trp_dbl, Team becomes team, Player-additional becomes player_id).
- Before dropping the League Average row, save its FG% value so Phase 4 can reconcile against it.
- Drop non-player rows, convert percentages to REAL, keep blanks as NULL, and write table player_stats to sql/nba.db.
- Create a view player_season with exactly one row per player: the combined row for traded players, the single row otherwise. Explain the logic in a comment.
- Commit once the loader works.

Phase 3: Queries
Write all 10 queries in sql/solutions.sql, each preceded by a comment with the question number, the question text, and a one-line note on logic and assumptions.
- Player-level questions (1, 2, 3, 4, 5, 7, 8, 10) use player_season.
- Team-level questions (6, 9) use player_stats and exclude combined rows (2TM, 3TM, etc.).
- Q2: for traded players, list the combined team code and say so in the note.
- Q4: average rebounds = AVG(trb) across player_season.
- Q7: PPG = CAST(pts AS REAL) / g. State whether you average player PPGs or compute SUM(pts) / SUM(g) per position, apply a stated minimum-games filter, and say how hybrid positions are handled.
- Q8: league average FG% = SUM(fg) / SUM(fga), not AVG(fg_pct). Apply a stated minimum FGA threshold to the player list.
- Q9: use RANK() and say why over DENSE_RANK().
- Q10: must use a CTE. State whether the average includes players with zero 3-point attempts.
- Watch SQLite integer division; cast to REAL wherever division happens.

Phase 4: Run, validate, and document
Run every query against sql/nba.db and generate sql/sql_solutions.md with:
- Header: engine (SQLite and exact version), dataset (season, source, download date), and data-cleaning decisions.
- For each question: the query in a code block, the result (top 10 to 15 rows for long results, with the total row count noted), and the logic note.
- A "Validation" section reporting the result of each check below. Report numbers, not just pass or fail:
  1. For every traded player, per-team rows sum to the combined row for pts, g, and ast. Report any mismatches.
  2. League FG% computed as SUM(fg) / SUM(fga) across player_season, compared with the saved League Average FG% (.471).
  3. player_season has exactly one row per player_id, and the Q1 answer equals that count.
  4. Recomputed fg / fga matches stored fg_pct within rounding; players with 0 FGA have NULL fg_pct, not 0.
  5. Distinct Pos values and how any hybrid positions were handled in Q7.
  6. Ties that affect the results of Q3, Q6, or Q9.
- Invoke /check-takehome to sanity-check the database.
- Flag anything that looks off rather than silently adjusting it.
- Commit once the doc is generated.
</instructions>

<constraints>
- Do not invent data or results. Every number in the doc must come from actually running a query.
- Readable SQL: consistent aliasing, one clause per line, no unnecessary subqueries.
- Never edit the expected values in /check-takehome.
</constraints>
