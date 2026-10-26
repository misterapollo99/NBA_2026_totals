"""Load the 2025-26 NBA season totals CSV into SQLite as player_stats.

Input:  data/nba_2025_26_totals.csv (Basketball Reference, Season Totals, CSV export)
Output: sql/nba.db with table player_stats, table league_average, and view player_season

Assumptions:
1. Player-additional (renamed player_id) is the unique player key. Names are kept for display
   only and never used to count or group players.
2. Column names are lowercased, % becomes _pct, other special characters become underscores,
   and a leading "3P" or "2P" becomes "fg3" or "fg2" so no name starts with a digit
   (3PA -> fg3a, 3P% -> fg3_pct). Player-additional becomes player_id.
3. The "League Average" row (player_id -9999) is not a player. Its percentages are saved to
   a one-row table league_average before the row is dropped, so the report can reconcile
   against Basketball Reference's own figure instead of a hard-coded number.
4. Repeated header rows (Player = "Player") are dropped too. The current file has none, but
   copies of Basketball Reference tables often do.
5. Percentages are already decimals in the file (".476"), so they are stored as REAL as is.
   A blank percentage means zero attempts and is stored as NULL, never 0. The loader checks
   that every NULL percentage lines up with zero attempts and fails if not.
6. Traded players have one combined row (team 2TM, 3TM, ...) plus one row per team. All rows
   are kept in player_stats; the player_season view picks one row per player.
7. The table and view are dropped and recreated on every run, so the load is repeatable.
8. data/ and sql/ are resolved relative to the repo root (this file's parent folder), so the
   loader runs from any directory.
"""

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "nba_2025_26_totals.csv"
DB_PATH = ROOT / "sql" / "nba.db"
LEAGUE_AVERAGE_ID = "-9999"

TEXT_COLUMNS = ["player", "team", "pos", "awards", "player_id"]
PCT_COLUMNS = ["fg_pct", "fg3_pct", "fg2_pct", "efg_pct", "ft_pct"]
# The attempts column that makes each percentage defined. eFG% is (FG + 0.5 * 3P) / FGA.
ATTEMPTS_FOR_PCT = {
    "fg_pct": "fga",
    "fg3_pct": "fg3a",
    "fg2_pct": "fg2a",
    "efg_pct": "fga",
    "ft_pct": "fta",
}

# Kept word for word in sync with the preamble of sql/solutions.sql; build_report.py checks it.
PLAYER_SEASON_VIEW = """\
-- player_season: exactly one row per player.
-- Basketball Reference lists a traded player once per team plus a combined row whose team
-- is 2TM, 3TM, ... and whose stats are the season totals. Keep the combined row for players
-- who have one, and the only row for everyone else. This relies on every multi-team player
-- having a combined row, which the validation section checks.
CREATE VIEW IF NOT EXISTS player_season AS
SELECT
    ps.*
FROM player_stats AS ps
WHERE ps.team GLOB '[0-9]*TM'
    OR ps.player_id NOT IN (
        SELECT
            player_id
        FROM player_stats
        WHERE team GLOB '[0-9]*TM'
    );
"""


def clean_column_name(name: str) -> str:
    if name == "Player-additional":
        return "player_id"
    cleaned = re.sub(r"^(\d)P", r"fg\1", name).lower().replace("%", "_pct")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return re.sub(r"_+", "_", cleaned)


def clean_columns(columns: list[str]) -> list[str]:
    cleaned = [clean_column_name(c) for c in columns]
    bad = [c for c in cleaned if not c or c[0].isdigit()]
    if bad or len(set(cleaned)) != len(cleaned):
        raise ValueError(f"column cleaning produced invalid or duplicate names: {cleaned}")
    return cleaned


def extract_league_average(frame: pd.DataFrame) -> dict[str, float | None]:
    rows = frame[frame["player_id"] == LEAGUE_AVERAGE_ID]
    if len(rows) != 1:
        raise ValueError(f"expected one League Average row, found {len(rows)}")
    row = rows.iloc[0]
    return {c: to_real(row[c]) for c in PCT_COLUMNS}


def drop_non_player_rows(frame: pd.DataFrame) -> pd.DataFrame:
    players = frame[(frame["player_id"] != LEAGUE_AVERAGE_ID) & (frame["player"] != "Player")]
    if (players["player_id"].str.strip() == "").any():
        raise ValueError("player rows without a player_id")
    return players


def to_real(text: str) -> float | None:
    return float(text) if text.strip() else None


def to_integer(text: str) -> int:
    # Counting stats are never blank for a real player; fail loudly if one is.
    return int(text)


def column_type(column: str) -> str:
    if column in TEXT_COLUMNS:
        return "TEXT"
    if column in PCT_COLUMNS:
        return "REAL"
    return "INTEGER"


def convert_value(column: str, text: str) -> str | int | float | None:
    kind = column_type(column)
    if kind == "TEXT":
        return text.strip() or None
    if kind == "REAL":
        return to_real(text)
    return to_integer(text)


def check_null_pcts_match_zero_attempts(rows: list[dict]) -> None:
    for pct, attempts in ATTEMPTS_FOR_PCT.items():
        for row in rows:
            if (row[pct] is None) != (row[attempts] == 0):
                raise ValueError(
                    f"{row['player_id']} {row['team']}: {pct}={row[pct]} with {attempts}="
                    f"{row[attempts]}"
                )


def write_database(rows: list[dict], columns: list[str], league: dict) -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("DROP VIEW IF EXISTS player_season")
        con.execute("DROP TABLE IF EXISTS player_stats")
        con.execute("DROP TABLE IF EXISTS league_average")

        column_defs = ",\n    ".join(f"{c} {column_type(c)}" for c in columns)
        con.execute(f"CREATE TABLE player_stats (\n    {column_defs}\n)")
        placeholders = ", ".join("?" for _ in columns)
        con.executemany(
            f"INSERT INTO player_stats ({', '.join(columns)}) VALUES ({placeholders})",
            [[row[c] for c in columns] for row in rows],
        )

        league_defs = ", ".join(f"{c} REAL" for c in PCT_COLUMNS)
        con.execute(f"CREATE TABLE league_average ({league_defs})")
        con.execute(
            f"INSERT INTO league_average VALUES ({', '.join('?' for _ in PCT_COLUMNS)})",
            [league[c] for c in PCT_COLUMNS],
        )

        # execute, not executescript: executescript commits first, so a failing view would
        # leave the new tables committed without it.
        con.execute(PLAYER_SEASON_VIEW)
        con.commit()
    finally:
        con.close()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    frame = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False, encoding="utf-8")
    frame.columns = clean_columns(list(frame.columns))

    league = extract_league_average(frame)
    players = drop_non_player_rows(frame)
    columns = list(players.columns)
    rows = [
        {c: convert_value(c, text) for c, text in zip(columns, values, strict=True)}
        for values in players.itertuples(index=False)
    ]
    check_null_pcts_match_zero_attempts(rows)
    write_database(rows, columns, league)

    con = sqlite3.connect(DB_PATH)
    try:
        stats = con.execute("SELECT COUNT(*) FROM player_stats").fetchone()[0]
        season = con.execute("SELECT COUNT(*) FROM player_season").fetchone()[0]
    finally:
        con.close()
    print(f"player_stats: {stats} rows, player_season: {season} rows")
    print(f"league_average.fg_pct: {league['fg_pct']}")
    print(f"dropped {len(frame) - len(players)} non-player row(s); wrote {DB_PATH}")


if __name__ == "__main__":
    main()
