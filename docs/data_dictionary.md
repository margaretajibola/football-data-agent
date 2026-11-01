# Data Dictionary

Data source: football-data.org, Premier League. `season_year` is the year the season starts, so 2026 means 2026/27. Team names include "FC" (for example "Arsenal FC"), so search with ILIKE, such as `team ILIKE '%arsenal%'`.

## analytics.match_results
Finished matches only.
- match_id, season_year, matchday, match_date
- home_team, away_team: team names
- home_goals, away_goals, total_goals
- winning_team: NULL for a draw
- result: HOME_WIN, AWAY_WIN or DRAW
- half_time_home, half_time_away

## analytics.upcoming_fixtures
- match_id, season_year, matchday, kickoff_utc, home_team, away_team

## analytics.team_match_stats
One row per team per finished match.
- team, opponent, venue (HOME or AWAY), match_date, matchday
- goals_for, goals_against
- result: W, D or L
- points: 3, 1 or 0

## analytics.league_table
- season_year, venue (ALL, HOME or AWAY), position, team
- played, won, drawn, lost, goals_for, goals_against, goal_diff, points
Use venue = 'ALL' for the normal table.

## analytics.team_form
- season_year, team
- form_last_5: for example 'WWDLW', most recent first
- points_last_5, goals_for_last_5, goals_against_last_5

## analytics.top_scorers
Latest snapshot. The free API tier may return only the top 10.
- player_name, nationality, position, team
- played_matches, goals, assists, penalties, goals_per_match

## analytics.teams
- team_id, name, short_name, tla, founded, stadium, club_colors

## Notes
- Results only include FINISHED matches. Future matches are in upcoming_fixtures.
- Tables are computed from match results, so they update whenever the load runs.