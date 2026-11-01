CREATE SCHEMA IF NOT EXISTS fd;

CREATE TABLE IF NOT EXISTS fd.teams (
    team_id      INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    short_name   TEXT,
    tla          TEXT,
    founded      INTEGER,
    venue        TEXT,
    club_colors  TEXT
);

CREATE TABLE IF NOT EXISTS fd.matches (
    match_id        INTEGER PRIMARY KEY,
    season_year     INTEGER,
    matchday        INTEGER,
    status          TEXT,
    utc_date        TIMESTAMPTZ,
    home_team_id    INTEGER REFERENCES fd.teams(team_id),
    away_team_id    INTEGER REFERENCES fd.teams(team_id),
    home_goals      INTEGER,
    away_goals      INTEGER,
    half_time_home  INTEGER,
    half_time_away  INTEGER,
    winner          TEXT,
    last_updated    TIMESTAMPTZ
);

-- one snapshot of the table per day, so we keep history
CREATE TABLE IF NOT EXISTS fd.standings (
    snapshot_date  DATE,
    season_year    INTEGER,
    table_type     TEXT,       -- TOTAL, HOME or AWAY
    position       INTEGER,
    team_id        INTEGER REFERENCES fd.teams(team_id),
    played         INTEGER,
    won            INTEGER,
    draw           INTEGER,
    lost           INTEGER,
    points         INTEGER,
    goals_for      INTEGER,
    goals_against  INTEGER,
    goal_diff      INTEGER,
    PRIMARY KEY (snapshot_date, table_type, team_id)
);

-- top scorers, one snapshot per day
CREATE TABLE IF NOT EXISTS fd.scorers (
    snapshot_date   DATE,
    season_year     INTEGER,
    player_id       INTEGER,
    player_name     TEXT,
    nationality     TEXT,
    position        TEXT,
    team_id         INTEGER REFERENCES fd.teams(team_id),
    played_matches  INTEGER,
    goals           INTEGER,
    assists         INTEGER,
    penalties       INTEGER,
    PRIMARY KEY (snapshot_date, player_id)
);

