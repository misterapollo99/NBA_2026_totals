"""Rebuild sql/nba.db, run every query, and write sql/sql_solutions.md plus result CSVs.

Inputs:  sql/solutions.sql (preamble + Q1..Q10), sql/validation.sql (V1..), sql/load_nba.py
Outputs: sql/sql_solutions.md, sql/results/qNN.csv, sql/results/vNN.csv

Assumptions:
1. Each query in the .sql files starts with a header comment "-- Q7. <question>" (or V7).
   Comment lines after it are the question text until a "-- Logic:" or "-- Note:" line;
   comment lines from there on are the note. The rest of the block is one SQL statement.
2. Everything in solutions.sql before Q1 is the preamble (the player_season view). It is
   executed as a script before Q1, never folded into a query or dropped.
3. The preamble's view must match PLAYER_SEASON_VIEW in load_nba.py word for word (ignoring
   whitespace), so the loader and the standalone file cannot drift apart.
4. The report proves the standalone claim: it copies player_stats into an empty in-memory
   database, runs the preamble there, reruns Q1..Q10, and compares with the main results.
5. Results with more than PREVIEW_ROWS rows show a preview in the doc; every result is
   written in full to a CSV and linked. NULL is shown as an empty cell.
6. A validation row whose "result" column is not "ok" is listed under Flags. Nothing is
   adjusted to make a check pass.
7. The doc has no timestamps, so rerunning on the same data gives an identical file.
8. Paths are resolved relative to this file, so the report builds from any directory.
"""

import csv
import platform
import re
import sqlite3
import sys
from pathlib import Path

import load_nba

SQL_DIR = Path(__file__).resolve().parent
SOLUTIONS = SQL_DIR / "solutions.sql"
VALIDATION = SQL_DIR / "validation.sql"
REPORT = SQL_DIR / "sql_solutions.md"
RESULTS = SQL_DIR / "results"
PREVIEW_ROWS = 15
DOWNLOAD_DATE = "2026-10-25"
HEADER = re.compile(r"^-- ([QV])(\d+)\. (.*)$")
NOTE_START = re.compile(r"^-- (Logic|Note): ?(.*)$")


def parse_blocks(text: str) -> tuple[str, list[dict]]:
    preamble, blocks, current = [], [], None
    for line in text.splitlines():
        header = HEADER.match(line)
        if header:
            kind, number, title = header.groups()
            current = {"id": f"{kind.lower()}{int(number):02d}", "label": f"{kind}{number}"}
            current |= {"title": [title], "note": [], "sql": [], "in_note": False}
            blocks.append(current)
        elif current is None:
            preamble.append(line)
        elif line.startswith("--") and not current["sql"]:
            note = NOTE_START.match(line)
            if note:
                current["in_note"] = True
                current["note"].append(note.group(2))
            else:
                target = "note" if current["in_note"] else "title"
                current[target].append(line[2:].strip())
        elif line.strip() or current["sql"]:
            current["sql"].append(line)
    for block in blocks:
        block["title"] = " ".join(block["title"])
        note = " ".join(block["note"])
        # The "Logic:" prefix is stripped, so the note itself may start lowercase.
        block["note"] = note[:1].upper() + note[1:]
        block["sql"] = "\n".join(block["sql"]).strip()
    return "\n".join(preamble), blocks


def normalize(sql: str) -> str:
    return " ".join(sql.split())


def check_view_in_sync(preamble: str) -> None:
    if normalize(load_nba.PLAYER_SEASON_VIEW) not in normalize(preamble):
        raise ValueError("player_season view in solutions.sql differs from load_nba.py")


def run_query(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]]:
    cursor = con.execute(sql)
    return [d[0] for d in cursor.description], cursor.fetchall()


def format_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        # Fixed notation so a small difference reads 0.00001, not 1e-05.
        return format(value, "f").rstrip("0").rstrip(".")
    return str(value).replace("|", "\\|")


def markdown_table(columns: list[str], rows: list[tuple]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(format_cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def write_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows([["" if v is None else v for v in row] for row in rows])


def render_result(block: dict, columns: list[str], rows: list[tuple]) -> list[str]:
    link = f"[results/{block['id']}.csv](results/{block['id']}.csv)"
    if not rows:
        return [f"Result: 0 rows. Full result: {link}"]
    count = f"{len(rows)} row{'s' if len(rows) != 1 else ''}"
    if len(rows) > PREVIEW_ROWS:
        count += f", first {PREVIEW_ROWS} shown"
    return [
        f"Result ({count}). Full result: {link}",
        "",
        markdown_table(columns, rows[:PREVIEW_ROWS]),
    ]


def run_standalone(preamble: str, questions: list[dict], expected: dict) -> list[tuple]:
    # Fresh in-memory copy with player_stats only, as a reviewer with their own load would have.
    source = sqlite3.connect(load_nba.DB_PATH)
    con = sqlite3.connect(":memory:")
    try:
        source.backup(con)
        con.execute("DROP VIEW player_season")
        con.execute("DROP TABLE league_average")
        con.executescript(preamble)
        view_rows = con.execute("SELECT COUNT(*) FROM player_season").fetchone()[0]
        matching = sum(run_query(con, q["sql"]) == expected[q["id"]] for q in questions)
    finally:
        con.close()
        source.close()
    result = "ok" if matching == len(questions) else "results differ"
    return [(view_rows, f"{matching} of {len(questions)}", result)]


def dataset_facts(con: sqlite3.Connection) -> dict:
    query = """
        SELECT
            COUNT(*),
            SUM(team GLOB '[0-9]*TM'),
            COUNT(DISTINCT player_id),
            COUNT(DISTINCT CASE WHEN team NOT GLOB '[0-9]*TM' THEN team END)
        FROM player_stats
    """
    rows, combined, players, teams = con.execute(query).fetchone()
    codes = con.execute(
        "SELECT DISTINCT team FROM player_stats WHERE team GLOB '[0-9]*TM' ORDER BY team"
    ).fetchall()
    league = con.execute("SELECT fg_pct, fg3_pct, ft_pct FROM league_average").fetchone()
    return {
        "rows": rows,
        "combined": combined,
        "combined_codes": ", ".join(f"`{code}`" for (code,) in codes),
        "players": players,
        "teams": teams,
        "league": league,
    }


def header_section(facts: dict) -> list[str]:
    fg, fg3, ft = facts["league"]
    return [
        "# SQL solutions: NBA 2025-26 season totals",
        "",
        f"- **Engine:** SQLite {sqlite3.sqlite_version}, run from Python "
        f"{platform.python_version()} with the standard `sqlite3` module.",
        "- **Dataset:** 2025-26 NBA player Season Totals from Basketball Reference "
        "(basketball-reference.com), exported with Share & more, Get as Excel/CSV. "
        f"Downloaded {DOWNLOAD_DATE}. File: `data/nba_2025_26_totals.csv`.",
        "- **Reproduce:** `.venv/Scripts/python sql/build_report.py` (reloads `sql/nba.db` "
        "with `sql/load_nba.py`, then runs `sql/solutions.sql` and `sql/validation.sql`).",
        "- **Files:** queries in `solutions.sql`, checks in `validation.sql`, every full "
        "result in `results/`.",
        "",
        "## Data cleaning decisions",
        "",
        "- Column names are lowercased, `%` becomes `_pct`, other special characters become "
        "underscores, and no name starts with a digit: `FG%` to `fg_pct`, `3P` to `fg3`, "
        "`3PA` to `fg3a`, `3P%` to `fg3_pct`, `2P` to `fg2`, `eFG%` to `efg_pct`, "
        "`Trp-Dbl` to `trp_dbl`, `Player-additional` to `player_id`.",
        "- `player_id` (Basketball Reference's Player-additional) is the player key. Names are "
        "for display only.",
        f"- The League Average row (`player_id` -9999) is not a player. Its percentages "
        f"(FG% {fg}, 3P% {fg3}, FT% {ft}) are saved to table `league_average` for "
        "reconciliation, then the row is dropped.",
        "- Percentages are already decimals in the file and are stored as REAL. A blank "
        "percentage means zero attempts and is stored as NULL, not 0. The loader fails if any "
        "NULL percentage does not line up with zero attempts.",
        f"- `player_stats` keeps all {facts['rows']} player rows: {facts['players']} players "
        f"on {facts['teams']} teams, including {facts['combined']} combined rows (team "
        f"{facts['combined_codes']}) for traded players alongside their per-team rows.",
        "- View `player_season` has one row per player: the combined row for traded players, "
        "the only row otherwise. Player-level questions (1, 2, 3, 4, 5, 7, 8, 10) use it.",
        "- Team-level questions (6, 9) use `player_stats` without combined rows, so a traded "
        "player counts for each team with the stats from that stint.",
        "- Every division casts to REAL first, because SQLite divides integers as integers.",
        "- `Trp-Dbl` and `Awards` are loaded but not used.",
        "",
    ]


def question_section(block: dict, columns: list[str], rows: list[tuple]) -> list[str]:
    return [
        f"## {block['label']}. {block['title']}",
        "",
        f"**Logic.** {block['note']}",
        "",
        "```sql",
        block["sql"],
        "```",
        "",
        *render_result(block, columns, rows),
        "",
    ]


def validation_section(block: dict, columns: list[str], rows: list[tuple]) -> list[str]:
    lines = [f"### {block['label']}. {block['title']}", ""]
    if block["note"]:
        lines += [block["note"], ""]
    if block["sql"]:
        lines += ["<details><summary>SQL</summary>", "", "```sql", block["sql"], "```", ""]
        lines += ["</details>", ""]
    return lines + [*render_result(block, columns, rows), ""]


def flagged_rows(label: str, title: str, columns: list[str], rows: list[tuple]) -> list[str]:
    if "result" not in columns:
        return []
    index = columns.index("result")
    return [
        f"- {label} ({title}): "
        + ", ".join(f"{c}={format_cell(v)}" for c, v in zip(columns, row, strict=True))
        for row in rows
        if row[index] != "ok"
    ]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_nba.main()

    preamble, questions = parse_blocks(SOLUTIONS.read_text(encoding="utf-8"))
    _, checks = parse_blocks(VALIDATION.read_text(encoding="utf-8"))
    check_view_in_sync(preamble)
    RESULTS.mkdir(exist_ok=True)

    con = sqlite3.connect(load_nba.DB_PATH)
    try:
        con.executescript(preamble)
        facts = dataset_facts(con)
        answers = {q["id"]: run_query(con, q["sql"]) for q in questions}
        outcomes = {v["id"]: run_query(con, v["sql"]) for v in checks}
    finally:
        con.close()

    standalone = {
        "id": "s01",
        "label": "S1",
        "title": "solutions.sql runs standalone",
        "note": "Copies player_stats into an empty in-memory database with no view, runs the "
        "preamble of solutions.sql, reruns Q1 to Q10, and compares every result with the "
        "results above.",
        "sql": "",
    }
    checks.append(standalone)
    outcomes["s01"] = (
        ["player_season_rows", "queries_with_identical_results", "result"],
        run_standalone(preamble, questions, answers),
    )

    q1_answer = answers["q01"][1][0][0]
    view_rows = outcomes["v04"][1][0][0]
    q1_line = (
        f"Q1 answer is {q1_answer}; player_season has {view_rows} rows; "
        f"{'equal' if q1_answer == view_rows else 'NOT EQUAL'}."
    )

    lines = header_section(facts)
    for q in questions:
        columns, rows = answers[q["id"]]
        write_csv(RESULTS / f"{q['id']}.csv", columns, rows)
        lines += question_section(q, columns, rows)

    lines += ["## Validation", ""]
    flags = [] if q1_answer == view_rows else [f"- V4: {q1_line}"]
    for v in checks:
        columns, rows = outcomes[v["id"]]
        write_csv(RESULTS / f"{v['id']}.csv", columns, rows)
        lines += validation_section(v, columns, rows)
        if v["id"] == "v04":
            lines += [q1_line, ""]
        flags += flagged_rows(v["label"], v["title"], columns, rows)

    lines += ["## Flags", ""]
    lines += flags or ["None."]
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"wrote {REPORT} with {len(questions)} queries, {len(checks)} checks, {len(flags)} flags")


if __name__ == "__main__":
    main()
