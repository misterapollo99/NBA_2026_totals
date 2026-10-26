-- SQL solutions: 2025-26 NBA season totals (Basketball Reference), SQLite.
-- Table player_stats is loaded by sql/load_nba.py. The view below is also created there;
-- it is repeated here so this file runs on its own against any player_stats table.

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

-- Q1. How many players played in the season?
-- Logic: one row per player in player_season, so COUNT(*) counts distinct player_ids.
-- Counting player_stats rows instead would count traded players two to five times.
SELECT
    COUNT(*) AS players
FROM player_season;

-- Q2. List the names and teams of all players who scored more than 1,000 total points.
-- Logic: season totals from player_season. For traded players, team is the combined code
-- (2TM, 3TM, ...) and teams lists the clubs they played for, in alphabetical order, from
-- their per-team rows. teams is blank for single-team players. GROUP_CONCAT runs as a
-- window function because plain GROUP_CONCAT has no guaranteed order before SQLite 3.44,
-- while a window's ORDER BY fixes the order on any version with window functions (3.25+).
WITH stints AS (
    SELECT
        player_id,
        GROUP_CONCAT(team, ', ') OVER (
            PARTITION BY player_id
            ORDER BY team
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS teams,
        COUNT(*) OVER (PARTITION BY player_id) AS team_count
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
),
traded AS (
    SELECT DISTINCT
        player_id,
        teams
    FROM stints
    WHERE team_count > 1
)
SELECT
    p.player,
    p.team,
    t.teams,
    p.pts
FROM player_season AS p
LEFT JOIN traded AS t
    ON t.player_id = p.player_id
WHERE p.pts > 1000
ORDER BY p.pts DESC, p.player;

-- Q3. Who are the top 5 players by total assists?
-- Logic: season totals from player_season, highest first. Player name breaks ties so the
-- order is stable; the validation section confirms no tie at the 5th place cutoff. As in Q2,
-- team is the combined code (2TM, 3TM, ...) for traded players and teams lists the clubs
-- they played for, in alphabetical order; teams is blank for single-team players.
WITH stints AS (
    SELECT
        player_id,
        GROUP_CONCAT(team, ', ') OVER (
            PARTITION BY player_id
            ORDER BY team
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS teams,
        COUNT(*) OVER (PARTITION BY player_id) AS team_count
    FROM player_stats
    WHERE team NOT GLOB '[0-9]*TM'
),
traded AS (
    SELECT DISTINCT
        player_id,
        teams
    FROM stints
    WHERE team_count > 1
)
SELECT
    p.player,
    p.team,
    t.teams,
    p.ast
FROM player_season AS p
LEFT JOIN traded AS t
    ON t.player_id = p.player_id
ORDER BY p.ast DESC, p.player
LIMIT 5;

-- Q4. What is the average number of rebounds per player?
-- Logic: this is total rebounds per player over the season, not rebounds per game.
-- AVG(trb) over player_season, so each player counts once with season total rebounds.
-- SQLite's AVG returns REAL, so there is no integer division.
SELECT
    ROUND(AVG(trb), 2) AS avg_rebounds
FROM player_season;

-- Q5. How many players had more steals than turnovers?
-- Logic: season totals from player_season; strictly more (equal counts are excluded).
SELECT
    COUNT(*) AS players
FROM player_season
WHERE stl > tov;

-- Q6. For each team, who scored the most total points?
-- Logic: per-team rows from player_stats, excluding combined rows (2TM, ...), which are not
-- teams. A traded player is credited only with points scored for that team. RANK() keeps
-- every player tied for first instead of picking one arbitrarily.
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

-- Q7. Which position (Pos) averaged the most points per game (PPG)?
-- Logic: PPG = CAST(pts AS REAL) / g per player, then the average of player PPGs per
-- position (the typical player at that position). Minimum 20 games, about a quarter of the
-- 82-game season, so short stints do not swing the average. Traded players use the Pos on
-- their combined row. The file has no hybrid positions (such as SG-PG); if it did, each
-- would be its own group. Without the games filter PG still leads (10.61 PPG), and PG also
-- leads when pooled as SUM(pts) / SUM(g) (see Validation).
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

-- Q8. List players whose field goal percentage (FG%) is higher than the league average.
-- Logic: league FG% = SUM(fg) / SUM(fga) over all players (0.4710, matching Basketball
-- Reference's .471). AVG(fg_pct) would weight a 2-shot player like a 1,500-shot player and
-- gives 0.4618. Players need at least 300 FGA, about 3.7 per game over 82 games, so tiny
-- samples do not qualify. Comparison uses unrounded fg / fga, not the 3-decimal fg_pct.
-- Without the FGA threshold, 241 players are above the league figure. The common naive
-- version, stored fg_pct > AVG(fg_pct) with no threshold, returns 273; the same comparison
-- on fg / fga returns 270. The three extra players have fg / fga of 0.4615 to four decimals
-- (6/13 and 12/26), which the stored column rounds up to 0.462, so they pass the comparison
-- with the 0.4618 average incorrectly (see Validation V9). fg_pct and league_fg_pct are
-- shown to 4 decimals with printf, which returns text so trailing zeros are kept.
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
    printf('%.4f', CAST(p.fg AS REAL) / p.fga) AS fg_pct,
    printf('%.4f', l.fg_pct) AS league_fg_pct
FROM player_season AS p
CROSS JOIN league AS l
WHERE p.fga >= 300
    AND CAST(p.fg AS REAL) / p.fga > l.fg_pct
ORDER BY CAST(p.fg AS REAL) / p.fga DESC, p.player;

-- Q9. For each team, rank players by points scored (use window functions).
-- Logic: per-team rows from player_stats, excluding combined rows, so a traded player is
-- ranked on each team with the points scored there. RANK() rather than DENSE_RANK(): tied
-- players share a rank and the next rank skips, so rank N means N-1 teammates scored more.
-- DENSE_RANK() would hide how many players are ahead; ROW_NUMBER() would break ties
-- arbitrarily.
SELECT
    team,
    player,
    pts,
    RANK() OVER (PARTITION BY team ORDER BY pts DESC) AS pts_rank
FROM player_stats
WHERE team NOT GLOB '[0-9]*TM'
ORDER BY team, pts_rank, player;

-- Q10. Using a CTE, calculate the average number of 3-pointers (3P) per player, then find
-- players who made more than double that average.
-- Logic: the CTE averages fg3 over every player in player_season, including those with zero
-- 3-point attempts, because they are players and the question asks per player. Excluding
-- them would raise the average from 56.21 to 59.81. Strictly more than double.
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
