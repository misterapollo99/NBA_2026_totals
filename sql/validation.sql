-- Validation checks for sql/solutions.sql. build_report.py runs each block and renders the
-- result. A row whose result column is not 'ok' is listed under Flags in the report.

-- V1. Traded players: per-team rows sum to the combined row (pts, g, ast)
-- Note: also checks that the number in the combined code (2TM -> 2) equals the number of
-- per-team rows. Mismatch columns count players, so 0 means every traded player reconciles.
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

-- V2. Multi-team players without a combined row
-- Note: player_season would return several rows for such a player. Expect no rows.
SELECT
    player_id,
    player,
    COUNT(*) AS team_rows,
    'missing combined row' AS result
FROM player_stats
GROUP BY player_id
HAVING COUNT(*) > 1
    AND SUM(team GLOB '[0-9]*TM') = 0;

-- V3. League FG%: SUM(fg) / SUM(fga) vs the saved League Average row
-- Note: avg_of_player_fg_pct is shown for contrast; it is not the league figure. The result
-- is ok when the computed value rounds to the saved 3-decimal figure.
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

-- V4. player_season has exactly one row per player_id
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

-- V5. Stored fg_pct vs recomputed fg / fga, and NULLs for zero attempts
-- Note: fg_pct is stored to 3 decimals, so differences up to 0.0005 are rounding. Covers all
-- player_stats rows, including per-team rows of traded players.
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

-- V6. Distinct Pos values
-- Note: is_hybrid marks values like SG-PG. Counts are players (player_season rows).
SELECT
    pos,
    COUNT(*) AS players,
    pos LIKE '%-%' AS is_hybrid
FROM player_season
GROUP BY pos
ORDER BY pos;

-- V7. Traded players whose Pos differs between teams
-- Note: Q7 uses season_pos, the Pos on the combined row. Listed as a flag so the choice is
-- visible, not because the data is wrong.
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

-- V8. Q7 robustness: position PPG under each method
-- Note: averaged = mean of player PPGs; pooled = SUM(pts) / SUM(g). The leader is the same
-- in every column when PG is first in each.
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

-- V9. Q8 sensitivity: players above league FG% by minimum FGA
-- Note: naive_avg_fg_pct_no_threshold is the common shortcut, stored fg_pct > AVG(fg_pct)
-- with no threshold, which the Q8 note quotes for contrast.
WITH league AS (
    SELECT
        CAST(SUM(fg) AS REAL) / SUM(fga) AS fg_pct,
        AVG(fg_pct) AS avg_fg_pct
    FROM player_season
),
shooters AS (
    SELECT
        p.fga,
        CAST(p.fg AS REAL) / p.fga > l.fg_pct AS above,
        p.fg_pct > l.avg_fg_pct AS above_naive
    FROM player_season AS p
    CROSS JOIN league AS l
    WHERE p.fga > 0
)
SELECT
    SUM(above) AS no_threshold,
    SUM(above AND fga >= 100) AS min_100_fga,
    SUM(above AND fga >= 200) AS min_200_fga,
    SUM(above AND fga >= 300) AS min_300_fga,
    SUM(fga >= 300) AS players_with_300_fga,
    SUM(above_naive) AS naive_avg_fg_pct_no_threshold
FROM shooters;

-- V10. Q10 sensitivity: average 3P with and without zero-attempt players
SELECT
    ROUND(AVG(fg3), 2) AS avg_fg3_all_players,
    SUM(fg3 > 2 * (SELECT AVG(fg3) FROM player_season)) AS above_double_all,
    ROUND(AVG(CASE WHEN fg3a > 0 THEN fg3 END), 2) AS avg_fg3_excluding_zero_3pa,
    SUM(fg3 > 2 * (SELECT AVG(fg3) FROM player_season WHERE fg3a > 0)) AS above_double_excluding,
    SUM(fg3a = 0) AS players_with_zero_3pa
FROM player_season;

-- V11. Q3 ties: assists around the top-5 cutoff
-- Note: with RANK(), a tie at 5th place puts more than 5 players at rank 5 or better, so
-- LIMIT 5 would drop one of them. ok means exactly 5 players rank in the top 5.
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

-- V12. Q6 ties: teams with more than one top scorer
-- Note: expect no rows.
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

-- V13. Q9 ties: players on the same team with equal points
-- Note: these players share a rank in Q9. Expected and handled by RANK(), so not a flag.
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
