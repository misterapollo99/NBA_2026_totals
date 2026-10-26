# SQL solutions: NBA 2025-26 season totals

- **Engine:** SQLite 3.49.1, run from Python 3.12.10 with the standard `sqlite3` module.
- **Dataset:** 2025-26 NBA player Season Totals from Basketball Reference (basketball-reference.com), exported with Share & more, Get as Excel/CSV. Downloaded 2026-10-25. File: `data/nba_2025_26_totals.csv`.
- **Reproduce:** `.venv/Scripts/python sql/build_report.py` (reloads `sql/nba.db` with `sql/load_nba.py`, then runs `sql/solutions.sql` and `sql/validation.sql`).
- **Files:** queries in `solutions.sql`, checks in `validation.sql`, every full result in `results/`.

## Data cleaning decisions

- Column names are lowercased, `%` becomes `_pct`, other special characters become underscores, and no name starts with a digit: `FG%` to `fg_pct`, `3P` to `fg3`, `3PA` to `fg3a`, `3P%` to `fg3_pct`, `2P` to `fg2`, `eFG%` to `efg_pct`, `Trp-Dbl` to `trp_dbl`, `Player-additional` to `player_id`.
- `player_id` (Basketball Reference's Player-additional) is the player key. Names are for display only.
- The League Average row (`player_id` -9999) is not a player. Its percentages (FG% 0.471, 3P% 0.36, FT% 0.783) are saved to table `league_average` for reconciliation, then the row is dropped.
- Percentages are already decimals in the file and are stored as REAL. A blank percentage means zero attempts and is stored as NULL, not 0. The loader fails if any NULL percentage does not line up with zero attempts.
- `player_stats` keeps all 733 player rows: 582 players on 30 teams, including 72 combined rows (team `2TM`, `3TM`, `4TM`) for traded players alongside their per-team rows.
- View `player_season` has one row per player: the combined row for traded players, the only row otherwise. Player-level questions (1, 2, 3, 4, 5, 7, 8, 10) use it.
- Team-level questions (6, 9) use `player_stats` without combined rows, so a traded player counts for each team with the stats from that stint.
- Every division casts to REAL first, because SQLite divides integers as integers.
- `Trp-Dbl` and `Awards` are loaded but not used.

## Q1. How many players played in the season?

**Logic.** One row per player in player_season, so COUNT(*) counts distinct player_ids. Counting player_stats rows instead would count traded players two to five times.

```sql
SELECT
    COUNT(*) AS players
FROM player_season;
```

Result (1 row). Full result: [results/q01.csv](results/q01.csv)

| players |
|---|
| 582 |

## Q2. List the names and teams of all players who scored more than 1,000 total points.

**Logic.** Season totals from player_season. For traded players, team is the combined code (2TM, 3TM, ...) and teams lists the clubs they played for, in alphabetical order, from their per-team rows. teams is blank for single-team players. GROUP_CONCAT with ORDER BY needs SQLite 3.44 or later.

```sql
WITH stints AS (
    SELECT
        player_id,
        GROUP_CONCAT(team, ', ' ORDER BY team) AS teams
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
    GROUP BY player_id
    HAVING COUNT(*) > 1
)
SELECT
    p.player,
    p.team,
    s.teams,
    p.pts
FROM player_season AS p
LEFT JOIN stints AS s
    ON s.player_id = p.player_id
WHERE p.pts > 1000
ORDER BY p.pts DESC, p.player;
```

Result (81 rows, first 15 shown). Full result: [results/q02.csv](results/q02.csv)

| player | team | teams | pts |
|---|---|---|---|
| Luka Dončić | LAL |  | 2143 |
| Shai Gilgeous-Alexander | OKC |  | 2117 |
| Jaylen Brown | BOS |  | 2038 |
| Kevin Durant | HOU |  | 2026 |
| Tyrese Maxey | PHI |  | 1980 |
| Donovan Mitchell | CLE |  | 1952 |
| Jalen Brunson | NYK |  | 1927 |
| Jamal Murray | DEN |  | 1905 |
| Kawhi Leonard | LAC |  | 1813 |
| Nikola Jokić | DEN |  | 1799 |
| Anthony Edwards | MIN |  | 1757 |
| Devin Booker | PHO |  | 1668 |
| Julius Randle | MIN |  | 1667 |
| Brandon Ingram | TOR |  | 1655 |
| James Harden | 2TM | CLE, LAC | 1652 |

## Q3. Who are the top 5 players by total assists?

**Logic.** Season totals from player_season, highest first. Player name breaks ties so the order is stable; the validation section confirms no tie at the 5th place cutoff.

```sql
SELECT
    player,
    team,
    ast
FROM player_season
ORDER BY ast DESC, player
LIMIT 5;
```

Result (5 rows). Full result: [results/q03.csv](results/q03.csv)

| player | team | ast |
|---|---|---|
| Nikola Jokić | DEN | 697 |
| Cade Cunningham | DET | 634 |
| Jalen Johnson | ATL | 566 |
| James Harden | 2TM | 557 |
| Jamal Murray | DEN | 535 |

## Q4. What is the average number of rebounds per player?

**Logic.** AVG(trb) over player_season, so each player counts once with season total rebounds. SQLite's AVG returns REAL, so there is no integer division.

```sql
SELECT
    ROUND(AVG(trb), 2) AS avg_rebounds
FROM player_season;
```

Result (1 row). Full result: [results/q04.csv](results/q04.csv)

| avg_rebounds |
|---|
| 185.01 |

## Q5. How many players had more steals than turnovers?

**Logic.** Season totals from player_season; strictly more (equal counts are excluded).

```sql
SELECT
    COUNT(*) AS players
FROM player_season
WHERE stl > tov;
```

Result (1 row). Full result: [results/q05.csv](results/q05.csv)

| players |
|---|
| 117 |

## Q6. For each team, who scored the most total points?

**Logic.** Per-team rows from player_stats, excluding combined rows (2TM, ...), which are not teams. A traded player is credited only with points scored for that team. RANK() keeps every player tied for first instead of picking one arbitrarily.

```sql
WITH ranked AS (
    SELECT
        team,
        player,
        pts,
        RANK() OVER (PARTITION BY team ORDER BY pts DESC) AS pts_rank
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
)
SELECT
    team,
    player,
    pts
FROM ranked
WHERE pts_rank = 1
ORDER BY team, player;
```

Result (30 rows, first 15 shown). Full result: [results/q06.csv](results/q06.csv)

| team | player | pts |
|---|---|---|
| ATL | Nickeil Alexander-Walker | 1624 |
| BOS | Jaylen Brown | 2038 |
| BRK | Michael Porter Jr. | 1259 |
| CHI | Matas Buzelis | 1252 |
| CHO | Kon Knueppel | 1498 |
| CLE | Donovan Mitchell | 1952 |
| DAL | Cooper Flagg | 1473 |
| DEN | Jamal Murray | 1905 |
| DET | Cade Cunningham | 1531 |
| GSW | Stephen Curry | 1142 |
| HOU | Kevin Durant | 2026 |
| IND | Pascal Siakam | 1485 |
| LAC | Kawhi Leonard | 1813 |
| LAL | Luka Dončić | 2143 |
| MEM | Jaylen Wells | 865 |

## Q7. Which position (Pos) averaged the most points per game (PPG)?

**Logic.** PPG = CAST(pts AS REAL) / g per player, then the average of player PPGs per position (the typical player at that position). Minimum 20 games, about a quarter of the 82-game season, so short stints do not swing the average. Traded players use the Pos on their combined row. The file has no hybrid positions (such as SG-PG); if it did, each would be its own group. Without the games filter PG still leads (10.61 PPG), and PG also leads when pooled as SUM(pts) / SUM(g) (see Validation).

```sql
WITH player_ppg AS (
    SELECT
        pos,
        CAST(pts AS REAL) / g AS ppg
    FROM player_season
    WHERE g >= 20
)
SELECT
    pos,
    COUNT(*) AS players,
    ROUND(AVG(ppg), 2) AS avg_ppg
FROM player_ppg
GROUP BY pos
ORDER BY avg_ppg DESC;
```

Result (5 rows). Full result: [results/q07.csv](results/q07.csv)

| pos | players | avg_ppg |
|---|---|---|
| PG | 76 | 12.11 |
| SF | 82 | 11.25 |
| PF | 87 | 9.87 |
| SG | 123 | 9.43 |
| C | 84 | 9.31 |

## Q8. List players whose field goal percentage (FG%) is higher than the league average.

**Logic.** League FG% = SUM(fg) / SUM(fga) over all players (0.4710, matching Basketball Reference's .471). AVG(fg_pct) would weight a 2-shot player like a 1,500-shot player and gives 0.4618. Players need at least 300 FGA, about 3.7 per game over 82 games, so tiny samples do not qualify. Comparison uses unrounded fg / fga, not the 3-decimal fg_pct. Without the FGA threshold, 241 players are above the league figure.

```sql
WITH league AS (
    SELECT
        CAST(SUM(fg) AS REAL) / SUM(fga) AS fg_pct
    FROM player_season
)
SELECT
    p.player,
    p.team,
    p.fg,
    p.fga,
    ROUND(CAST(p.fg AS REAL) / p.fga, 3) AS fg_pct,
    ROUND(l.fg_pct, 4) AS league_fg_pct
FROM player_season AS p
CROSS JOIN league AS l
WHERE p.fga >= 300
    AND CAST(p.fg AS REAL) / p.fga > l.fg_pct
ORDER BY CAST(p.fg AS REAL) / p.fga DESC, p.player;
```

Result (120 rows, first 15 shown). Full result: [results/q08.csv](results/q08.csv)

| player | team | fg | fga | fg_pct | league_fg_pct |
|---|---|---|---|---|---|
| Jakob Poeltl | TOR | 217 | 310 | 0.7 | 0.471 |
| Rudy Gobert | MIN | 335 | 491 | 0.682 | 0.471 |
| Deandre Ayton | LAL | 403 | 601 | 0.671 | 0.471 |
| Daniel Gafford | DAL | 207 | 316 | 0.655 | 0.471 |
| Neemias Queta | BOS | 326 | 499 | 0.653 | 0.471 |
| Oso Ighodaro | PHO | 239 | 366 | 0.653 | 0.471 |
| Jalen Duren | DET | 522 | 803 | 0.65 | 0.471 |
| Mark Williams | PHO | 282 | 438 | 0.644 | 0.471 |
| Jarrett Allen | CLE | 337 | 528 | 0.638 | 0.471 |
| Moussa Diabaté | CHO | 229 | 363 | 0.631 | 0.471 |
| Giannis Antetokounmpo | MIL | 373 | 598 | 0.624 | 0.471 |
| Marvin Bagley III | 2TM | 254 | 411 | 0.618 | 0.471 |
| Paul Reed | DET | 209 | 339 | 0.617 | 0.471 |
| Day'Ron Sharpe | BRK | 214 | 356 | 0.601 | 0.471 |
| Zion Williamson | NOP | 484 | 807 | 0.6 | 0.471 |

## Q9. For each team, rank players by points scored (use window functions).

**Logic.** Per-team rows from player_stats, excluding combined rows, so a traded player is ranked on each team with the points scored there. RANK() rather than DENSE_RANK(): tied players share a rank and the next rank skips, so rank N means N-1 teammates scored more. DENSE_RANK() would hide how many players are ahead; ROW_NUMBER() would break ties arbitrarily.

```sql
SELECT
    team,
    player,
    pts,
    RANK() OVER (PARTITION BY team ORDER BY pts DESC) AS pts_rank
FROM player_stats
WHERE team NOT GLOB '[0-9]*TM'
ORDER BY team, pts_rank, player;
```

Result (661 rows, first 15 shown). Full result: [results/q09.csv](results/q09.csv)

| team | player | pts | pts_rank |
|---|---|---|---|
| ATL | Nickeil Alexander-Walker | 1624 | 1 |
| ATL | Jalen Johnson | 1621 | 2 |
| ATL | Onyeka Okongwu | 1123 | 3 |
| ATL | Dyson Daniels | 901 | 4 |
| ATL | CJ McCollum | 766 | 5 |
| ATL | Zaccharie Risacher | 641 | 6 |
| ATL | Vít Krejčí | 414 | 7 |
| ATL | Luke Kennard | 364 | 8 |
| ATL | Corey Kispert | 358 | 9 |
| ATL | Mouhamed Gueye | 342 | 10 |
| ATL | Kristaps Porziņģis | 291 | 11 |
| ATL | Asa Newell | 227 | 12 |
| ATL | Jock Landale | 209 | 13 |
| ATL | Jonathan Kuminga | 196 | 14 |
| ATL | Trae Young | 193 | 15 |

## Q10. Using a CTE, calculate the average number of 3-pointers (3P) per player, then find players who made more than double that average.

**Logic.** The CTE averages fg3 over every player in player_season, including those with zero 3-point attempts, because they are players and the question asks per player. Excluding them would raise the average from 56.21 to 59.81. Strictly more than double.

```sql
WITH league AS (
    SELECT
        AVG(fg3) AS avg_fg3
    FROM player_season
)
SELECT
    p.player,
    p.team,
    p.fg3,
    ROUND(l.avg_fg3, 2) AS avg_fg3
FROM player_season AS p
CROSS JOIN league AS l
WHERE p.fg3 > 2 * l.avg_fg3
ORDER BY p.fg3 DESC, p.player;
```

Result (100 rows, first 15 shown). Full result: [results/q10.csv](results/q10.csv)

| player | team | fg3 | avg_fg3 |
|---|---|---|---|
| Kon Knueppel | CHO | 273 | 56.21 |
| LaMelo Ball | CHO | 272 | 56.21 |
| Luka Dončić | LAL | 254 | 56.21 |
| Nickeil Alexander-Walker | ATL | 251 | 56.21 |
| Jamal Murray | DEN | 245 | 56.21 |
| Donte DiVincenzo | MIN | 244 | 56.21 |
| A.J. Green | MIL | 232 | 56.21 |
| Collin Gillespie | PHO | 232 | 56.21 |
| Reed Sheppard | HOU | 227 | 56.21 |
| Donovan Mitchell | CLE | 224 | 56.21 |
| Tim Hardaway Jr. | DEN | 224 | 56.21 |
| Duncan Robinson | DET | 220 | 56.21 |
| Tyrese Maxey | PHI | 220 | 56.21 |
| Toumani Camara | POR | 219 | 56.21 |
| James Harden | 2TM | 215 | 56.21 |

## Validation

### V1. Traded players: per-team rows sum to the combined row (pts, g, ast)

Also checks that the number in the combined code (2TM -> 2) equals the number of per-team rows. Mismatch columns count players, so 0 means every traded player reconciles.

<details><summary>SQL</summary>

```sql
WITH combined AS (
    SELECT
        player_id,
        team,
        pts,
        g,
        ast
    FROM player_stats
    WHERE team GLOB '[0-9]*TM'
),
stints AS (
    SELECT
        player_id,
        COUNT(*) AS stint_rows,
        SUM(pts) AS pts,
        SUM(g) AS g,
        SUM(ast) AS ast
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
    GROUP BY player_id
),
compared AS (
    SELECT
        c.player_id,
        CAST(c.team AS INTEGER) <> COALESCE(s.stint_rows, 0) AS bad_rows,
        c.pts <> s.pts AS bad_pts,
        c.g <> s.g AS bad_g,
        c.ast <> s.ast AS bad_ast
    FROM combined AS c
    LEFT JOIN stints AS s
        ON s.player_id = c.player_id
)
SELECT
    COUNT(*) AS traded_players,
    SUM(bad_rows) AS stint_count_mismatches,
    SUM(bad_pts) AS pts_mismatches,
    SUM(bad_g) AS g_mismatches,
    SUM(bad_ast) AS ast_mismatches,
    CASE
        WHEN SUM(bad_rows) + SUM(bad_pts) + SUM(bad_g) + SUM(bad_ast) = 0 THEN 'ok'
        ELSE 'mismatch'
    END AS result
FROM compared;
```

</details>

Result (1 row). Full result: [results/v01.csv](results/v01.csv)

| traded_players | stint_count_mismatches | pts_mismatches | g_mismatches | ast_mismatches | result |
|---|---|---|---|---|---|
| 72 | 0 | 0 | 0 | 0 | ok |

### V2. Multi-team players without a combined row

Player_season would return several rows for such a player. Expect no rows.

<details><summary>SQL</summary>

```sql
SELECT
    player_id,
    player,
    COUNT(*) AS team_rows,
    'missing combined row' AS result
FROM player_stats
GROUP BY player_id
HAVING COUNT(*) > 1
    AND SUM(team GLOB '[0-9]*TM') = 0;
```

</details>

Result: 0 rows. Full result: [results/v02.csv](results/v02.csv)

### V3. League FG%: SUM(fg) / SUM(fga) vs the saved League Average row

Avg_of_player_fg_pct is shown for contrast; it is not the league figure. The result is ok when the computed value rounds to the saved 3-decimal figure.

<details><summary>SQL</summary>

```sql
WITH computed AS (
    SELECT
        CAST(SUM(fg) AS REAL) / SUM(fga) AS pooled_fg_pct,
        AVG(fg_pct) AS avg_of_player_fg_pct
    FROM player_season
)
SELECT
    ROUND(c.pooled_fg_pct, 5) AS sum_fg_over_sum_fga,
    la.fg_pct AS league_average_row,
    ROUND(c.pooled_fg_pct - la.fg_pct, 5) AS difference,
    ROUND(c.avg_of_player_fg_pct, 4) AS avg_of_player_fg_pct,
    CASE
        WHEN ROUND(c.pooled_fg_pct, 3) = la.fg_pct THEN 'ok'
        ELSE 'differs'
    END AS result
FROM computed AS c
CROSS JOIN league_average AS la;
```

</details>

Result (1 row). Full result: [results/v03.csv](results/v03.csv)

| sum_fg_over_sum_fga | league_average_row | difference | avg_of_player_fg_pct | result |
|---|---|---|---|---|
| 0.47101 | 0.471 | 0.00001 | 0.4618 | ok |

### V4. player_season has exactly one row per player_id

<details><summary>SQL</summary>

```sql
SELECT
    (SELECT COUNT(*) FROM player_season) AS player_season_rows,
    (SELECT COUNT(DISTINCT player_id) FROM player_season) AS distinct_ids_in_view,
    (SELECT COUNT(DISTINCT player_id) FROM player_stats) AS distinct_ids_in_table,
    CASE
        WHEN (SELECT COUNT(*) FROM player_season)
            = (SELECT COUNT(DISTINCT player_id) FROM player_season)
            AND (SELECT COUNT(*) FROM player_season)
            = (SELECT COUNT(DISTINCT player_id) FROM player_stats)
            THEN 'ok'
        ELSE 'duplicate or missing players'
    END AS result;
```

</details>

Result (1 row). Full result: [results/v04.csv](results/v04.csv)

| player_season_rows | distinct_ids_in_view | distinct_ids_in_table | result |
|---|---|---|---|
| 582 | 582 | 582 | ok |

Q1 answer is 582; player_season has 582 rows; equal.

### V5. Stored fg_pct vs recomputed fg / fga, and NULLs for zero attempts

Fg_pct is stored to 3 decimals, so differences up to 0.0005 are rounding. Covers all player_stats rows, including per-team rows of traded players.

<details><summary>SQL</summary>

```sql
SELECT
    COUNT(*) AS rows_checked,
    ROUND(MAX(ABS(CAST(fg AS REAL) / NULLIF(fga, 0) - fg_pct)), 6) AS max_abs_difference,
    SUM(fga = 0) AS zero_fga_rows,
    SUM(fga = 0 AND fg_pct IS NULL) AS zero_fga_with_null_pct,
    SUM(fga = 0 AND fg_pct IS NOT NULL) AS zero_fga_with_value,
    SUM(fga > 0 AND fg_pct IS NULL) AS attempts_but_null_pct,
    CASE
        WHEN MAX(ABS(CAST(fg AS REAL) / NULLIF(fga, 0) - fg_pct)) <= 0.0005 + 1e-9
            AND SUM(fga = 0 AND fg_pct IS NOT NULL) = 0
            AND SUM(fga > 0 AND fg_pct IS NULL) = 0
            THEN 'ok'
        ELSE 'mismatch'
    END AS result
FROM player_stats;
```

</details>

Result (1 row). Full result: [results/v05.csv](results/v05.csv)

| rows_checked | max_abs_difference | zero_fga_rows | zero_fga_with_null_pct | zero_fga_with_value | attempts_but_null_pct | result |
|---|---|---|---|---|---|---|
| 733 | 0.0005 | 3 | 3 | 0 | 0 | ok |

### V6. Distinct Pos values

Is_hybrid marks values like SG-PG. Counts are players (player_season rows).

<details><summary>SQL</summary>

```sql
SELECT
    pos,
    COUNT(*) AS players,
    pos LIKE '%-%' AS is_hybrid
FROM player_season
GROUP BY pos
ORDER BY pos;
```

</details>

Result (5 rows). Full result: [results/v06.csv](results/v06.csv)

| pos | players | is_hybrid |
|---|---|---|
| C | 107 | 0 |
| PF | 106 | 0 |
| PG | 97 | 0 |
| SF | 111 | 0 |
| SG | 161 | 0 |

### V7. Traded players whose Pos differs between teams

Q7 uses season_pos, the Pos on the combined row. Listed as a flag so the choice is visible, not because the data is wrong.

<details><summary>SQL</summary>

```sql
SELECT
    ps.player,
    ps.pos AS season_pos,
    GROUP_CONCAT(st.team || ' ' || st.pos, ', ' ORDER BY st.team) AS pos_by_team,
    'Pos differs across teams; Q7 uses season_pos' AS result
FROM player_season AS ps
JOIN player_stats AS st
    ON st.player_id = ps.player_id
    AND st.team NOT GLOB '[0-9]*TM'
GROUP BY ps.player_id
HAVING COUNT(DISTINCT st.pos) > 1
ORDER BY ps.player;
```

</details>

Result (5 rows). Full result: [results/v07.csv](results/v07.csv)

| player | season_pos | pos_by_team | result |
|---|---|---|---|
| CJ McCollum | PG | ATL PG, WAS SG | Pos differs across teams; Q7 uses season_pos |
| Josh Minott | PF | BOS PF, BRK SF | Pos differs across teams; Q7 uses season_pos |
| Keshon Gilbert | SG | ATL SG, WAS PG | Pos differs across teams; Q7 uses season_pos |
| Kevin Huerter | SF | CHI SF, DET SG | Pos differs across teams; Q7 uses season_pos |
| Vince Williams Jr. | SG | MEM PG, UTA SG | Pos differs across teams; Q7 uses season_pos |

### V8. Q7 robustness: position PPG under each method

Averaged = mean of player PPGs; pooled = SUM(pts) / SUM(g). The leader is the same in every column when PG is first in each.

<details><summary>SQL</summary>

```sql
SELECT
    pos,
    ROUND(AVG(CASE WHEN g >= 20 THEN CAST(pts AS REAL) / g END), 2) AS averaged_min_20_g,
    ROUND(AVG(CAST(pts AS REAL) / g), 2) AS averaged_no_filter,
    ROUND(
        CAST(SUM(CASE WHEN g >= 20 THEN pts END) AS REAL) / SUM(CASE WHEN g >= 20 THEN g END),
        2
    ) AS pooled_min_20_g,
    ROUND(CAST(SUM(pts) AS REAL) / SUM(g), 2) AS pooled_no_filter
FROM player_season
GROUP BY pos
ORDER BY averaged_min_20_g DESC;
```

</details>

Result (5 rows). Full result: [results/v08.csv](results/v08.csv)

| pos | averaged_min_20_g | averaged_no_filter | pooled_min_20_g | pooled_no_filter |
|---|---|---|---|---|
| PG | 12.11 | 10.61 | 12.72 | 12.38 |
| SF | 11.25 | 9.58 | 12.07 | 11.73 |
| PF | 9.87 | 9.05 | 10.35 | 10.26 |
| SG | 9.43 | 8.61 | 9.95 | 9.78 |
| C | 9.31 | 8.33 | 9.91 | 9.75 |

### V9. Q8 sensitivity: players above league FG% by minimum FGA

<details><summary>SQL</summary>

```sql
WITH league AS (
    SELECT
        CAST(SUM(fg) AS REAL) / SUM(fga) AS fg_pct
    FROM player_season
),
shooters AS (
    SELECT
        p.fga,
        CAST(p.fg AS REAL) / p.fga > l.fg_pct AS above
    FROM player_season AS p
    CROSS JOIN league AS l
    WHERE p.fga > 0
)
SELECT
    SUM(above) AS no_threshold,
    SUM(above AND fga >= 100) AS min_100_fga,
    SUM(above AND fga >= 200) AS min_200_fga,
    SUM(above AND fga >= 300) AS min_300_fga,
    SUM(fga >= 300) AS players_with_300_fga
FROM shooters;
```

</details>

Result (1 row). Full result: [results/v09.csv](results/v09.csv)

| no_threshold | min_100_fga | min_200_fga | min_300_fga | players_with_300_fga |
|---|---|---|---|---|
| 241 | 179 | 148 | 120 | 284 |

### V10. Q10 sensitivity: average 3P with and without zero-attempt players

<details><summary>SQL</summary>

```sql
SELECT
    ROUND(AVG(fg3), 2) AS avg_fg3_all_players,
    SUM(fg3 > 2 * (SELECT AVG(fg3) FROM player_season)) AS above_double_all,
    ROUND(AVG(CASE WHEN fg3a > 0 THEN fg3 END), 2) AS avg_fg3_excluding_zero_3pa,
    SUM(fg3 > 2 * (SELECT AVG(fg3) FROM player_season WHERE fg3a > 0)) AS above_double_excluding,
    SUM(fg3a = 0) AS players_with_zero_3pa
FROM player_season;
```

</details>

Result (1 row). Full result: [results/v10.csv](results/v10.csv)

| avg_fg3_all_players | above_double_all | avg_fg3_excluding_zero_3pa | above_double_excluding | players_with_zero_3pa |
|---|---|---|---|---|
| 56.21 | 100 | 59.81 | 88 | 35 |

### V11. Q3 ties: assists around the top-5 cutoff

With RANK(), a tie at 5th place puts more than 5 players at rank 5 or better, so LIMIT 5 would drop one of them. ok means exactly 5 players rank in the top 5.

<details><summary>SQL</summary>

```sql
WITH ranked AS (
    SELECT
        player,
        ast,
        RANK() OVER (ORDER BY ast DESC) AS ast_rank
    FROM player_season
)
SELECT
    player,
    ast,
    ast_rank,
    CASE
        WHEN (SELECT COUNT(*) FROM ranked WHERE ast_rank <= 5) = 5 THEN 'ok'
        ELSE 'tie at cutoff'
    END AS result
FROM ranked
WHERE ast_rank BETWEEN 4 AND 7
ORDER BY ast_rank, player;
```

</details>

Result (4 rows). Full result: [results/v11.csv](results/v11.csv)

| player | ast | ast_rank | result |
|---|---|---|---|
| James Harden | 557 | 4 | ok |
| Jamal Murray | 535 | 5 | ok |
| Luka Dončić | 530 | 6 | ok |
| LaMelo Ball | 514 | 7 | ok |

### V12. Q6 ties: teams with more than one top scorer

Expect no rows.

<details><summary>SQL</summary>

```sql
WITH ranked AS (
    SELECT
        team,
        player,
        RANK() OVER (PARTITION BY team ORDER BY pts DESC) AS pts_rank
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
)
SELECT
    team,
    COUNT(*) AS tied_leaders,
    GROUP_CONCAT(player, ', ' ORDER BY player) AS players,
    'tie for top scorer' AS result
FROM ranked
WHERE pts_rank = 1
GROUP BY team
HAVING COUNT(*) > 1;
```

</details>

Result: 0 rows. Full result: [results/v12.csv](results/v12.csv)

### V13. Q9 ties: players on the same team with equal points

These players share a rank in Q9. Expected and handled by RANK(), so not a flag.

<details><summary>SQL</summary>

```sql
SELECT
    team,
    pts,
    COUNT(*) AS players_tied,
    GROUP_CONCAT(player, ', ' ORDER BY player) AS players
FROM player_stats
WHERE team NOT GLOB '[0-9]*TM'
GROUP BY team, pts
HAVING COUNT(*) > 1
ORDER BY pts DESC, team;
```

</details>

Result (6 rows). Full result: [results/v13.csv](results/v13.csv)

| team | pts | players_tied | players |
|---|---|---|---|
| LAL | 288 | 2 | Jarred Vanderbilt, Luke Kennard |
| GSW | 242 | 2 | Jonathan Kuminga, Kristaps Porziņģis |
| ORL | 215 | 2 | Jamal Cain, Jevon Carter |
| MIN | 41 | 2 | Joe Ingles, Julian Phillips |
| ATL | 11 | 2 | Keshon Gilbert, Tony Bradley |
| TOR | 0 | 2 | Chucky Hepburn, Mo Bamba |

### S1. solutions.sql runs standalone

Copies player_stats into an empty in-memory database with no view, runs the preamble of solutions.sql, reruns Q1 to Q10, and compares every result with the results above.

Result (1 row). Full result: [results/s01.csv](results/s01.csv)

| player_season_rows | queries_with_identical_results | result |
|---|---|---|
| 582 | 10 of 10 | ok |

## Flags

- V7 (Traded players whose Pos differs between teams): player=CJ McCollum, season_pos=PG, pos_by_team=ATL PG, WAS SG, result=Pos differs across teams; Q7 uses season_pos
- V7 (Traded players whose Pos differs between teams): player=Josh Minott, season_pos=PF, pos_by_team=BOS PF, BRK SF, result=Pos differs across teams; Q7 uses season_pos
- V7 (Traded players whose Pos differs between teams): player=Keshon Gilbert, season_pos=SG, pos_by_team=ATL SG, WAS PG, result=Pos differs across teams; Q7 uses season_pos
- V7 (Traded players whose Pos differs between teams): player=Kevin Huerter, season_pos=SF, pos_by_team=CHI SF, DET SG, result=Pos differs across teams; Q7 uses season_pos
- V7 (Traded players whose Pos differs between teams): player=Vince Williams Jr., season_pos=SG, pos_by_team=MEM PG, UTA SG, result=Pos differs across teams; Q7 uses season_pos
