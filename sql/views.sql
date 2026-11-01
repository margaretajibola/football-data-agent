CREATE SCHEMA IF NOT EXISTS analytics;

-- drop in one go so the views can be changed and rerun safely
DROP VIEW IF EXISTS analytics.team_match_stats CASCADE;
DROP VIEW IF EXISTS analytics.match_results CASCADE;
DROP VIEW IF EXISTS analytics.upcoming_fixtures CASCADE;
DROP VIEW IF EXISTS analytics.top_scorers CASCADE;
DROP VIEW IF EXISTS analytics.teams CASCADE;


-- one row per finished match, with team names and the result
CREATE VIEW analytics.match_results AS
SELECT m.match_id, m.season_year, m.matchday, m.utc_date::date AS match_date,
       h.name AS home_team, a.name AS away_team,
       m.home_goals, m.away_goals,
       m.home_goals + m.away_goals AS total_goals,
       CASE m.winner WHEN 'HOME_TEAM' THEN h.name
                     WHEN 'AWAY_TEAM' THEN a.name END AS winning_team,
       CASE m.winner WHEN 'HOME_TEAM' THEN 'HOME_WIN'
                     WHEN 'AWAY_TEAM' THEN 'AWAY_WIN'
                     ELSE 'DRAW' END AS result,
       m.half_time_home, m.half_time_away
FROM fd.matches m
JOIN fd.teams h ON h.team_id = m.home_team_id
JOIN fd.teams a ON a.team_id = m.away_team_id
WHERE m.status = 'FINISHED';


-- matches that have not been played yet
CREATE VIEW analytics.upcoming_fixtures AS
SELECT m.match_id, m.season_year, m.matchday, m.utc_date AS kickoff_utc,
       h.name AS home_team, a.name AS away_team
FROM fd.matches m
JOIN fd.teams h ON h.team_id = m.home_team_id
JOIN fd.teams a ON a.team_id = m.away_team_id
WHERE m.status IN ('SCHEDULED', 'TIMED');


-- one row per team per finished match, the base for tables and form
CREATE VIEW analytics.team_match_stats AS
SELECT m.match_id, m.season_year, m.matchday, m.utc_date::date AS match_date,
       t.name AS team, o.name AS opponent, 'HOME'::text AS venue,
       m.home_goals AS goals_for, m.away_goals AS goals_against,
       CASE WHEN m.home_goals > m.away_goals THEN 'W'
            WHEN m.home_goals = m.away_goals THEN 'D' ELSE 'L' END AS result,
       CASE WHEN m.home_goals > m.away_goals THEN 3
            WHEN m.home_goals = m.away_goals THEN 1 ELSE 0 END AS points
FROM fd.matches m
JOIN fd.teams t ON t.team_id = m.home_team_id
JOIN fd.teams o ON o.team_id = m.away_team_id
WHERE m.status = 'FINISHED'
UNION ALL
SELECT m.match_id, m.season_year, m.matchday, m.utc_date::date,
       t.name, o.name, 'AWAY'::text,
       m.away_goals, m.home_goals,
       CASE WHEN m.away_goals > m.home_goals THEN 'W'
            WHEN m.away_goals = m.home_goals THEN 'D' ELSE 'L' END,
       CASE WHEN m.away_goals > m.home_goals THEN 3
            WHEN m.away_goals = m.home_goals THEN 1 ELSE 0 END
FROM fd.matches m
JOIN fd.teams t ON t.team_id = m.away_team_id
JOIN fd.teams o ON o.team_id = m.home_team_id
WHERE m.status = 'FINISHED';


-- league table worked out from results, for all, home only and away only
CREATE VIEW analytics.league_table AS
WITH agg AS (
    SELECT season_year, team, 'ALL'::text AS venue,
           COUNT(*) AS played,
           COUNT(*) FILTER (WHERE result = 'W') AS won,
           COUNT(*) FILTER (WHERE result = 'D') AS drawn,
           COUNT(*) FILTER (WHERE result = 'L') AS lost,
           SUM(goals_for) AS goals_for,
           SUM(goals_against) AS goals_against,
           SUM(goals_for) - SUM(goals_against) AS goal_diff,
           SUM(points) AS points
    FROM analytics.team_match_stats
    GROUP BY season_year, team
    UNION ALL
    SELECT season_year, team, venue,
           COUNT(*),
           COUNT(*) FILTER (WHERE result = 'W'),
           COUNT(*) FILTER (WHERE result = 'D'),
           COUNT(*) FILTER (WHERE result = 'L'),
           SUM(goals_for),
           SUM(goals_against),
           SUM(goals_for) - SUM(goals_against),
           SUM(points)
    FROM analytics.team_match_stats
    GROUP BY season_year, team, venue
)
SELECT season_year, venue,
       RANK() OVER (PARTITION BY season_year, venue
                    ORDER BY points DESC, goal_diff DESC, goals_for DESC) AS position,
       team, played, won, drawn, lost, goals_for, goals_against, goal_diff, points
FROM agg;


-- results of each team's last 5 finished matches, most recent first
CREATE VIEW analytics.team_form AS
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY season_year, team
                                 ORDER BY match_date DESC, match_id DESC) AS rn
    FROM analytics.team_match_stats
)
SELECT season_year, team,
       string_agg(result, '' ORDER BY match_date DESC, match_id DESC) AS form_last_5,
       SUM(points) AS points_last_5,
       SUM(goals_for) AS goals_for_last_5,
       SUM(goals_against) AS goals_against_last_5
FROM ranked
WHERE rn <= 5
GROUP BY season_year, team;


-- latest top scorers snapshot
CREATE VIEW analytics.top_scorers AS
SELECT s.season_year, s.snapshot_date, s.player_name, s.nationality, s.position,
       t.name AS team, s.played_matches, s.goals, s.assists, s.penalties,
       ROUND(s.goals::numeric / NULLIF(s.played_matches, 0), 2) AS goals_per_match
FROM fd.scorers s
JOIN fd.teams t ON t.team_id = s.team_id
WHERE s.snapshot_date = (SELECT MAX(snapshot_date) FROM fd.scorers);


-- club information
CREATE VIEW analytics.teams AS
SELECT team_id, name, short_name, tla, founded, venue AS stadium, club_colors
FROM fd.teams;


COMMENT ON VIEW analytics.match_results IS 'One row per finished Premier League match with team names, score and result.';
COMMENT ON VIEW analytics.upcoming_fixtures IS 'Matches that have not been played yet.';
COMMENT ON VIEW analytics.team_match_stats IS 'One row per team per finished match: opponent, home or away, goals, result (W/D/L) and points.';
COMMENT ON VIEW analytics.league_table IS 'League table computed from results. Use venue ALL, HOME or AWAY.';
COMMENT ON VIEW analytics.team_form IS 'Form over each team''s last 5 finished matches, most recent first.';
COMMENT ON VIEW analytics.top_scorers IS 'Latest snapshot of the top scorers.';
COMMENT ON VIEW analytics.teams IS 'Club information.';