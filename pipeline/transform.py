# turn the raw API JSON into rows that match the tables


def teams_rows(raw):
    return [
        (t["id"], t["name"], t.get("shortName"), t.get("tla"),
         t.get("founded"), t.get("venue"), t.get("clubColors"))
        for t in raw["teams"]
    ]


def matches_rows(raw):
    rows = []
    for m in raw["matches"]:
        full = m["score"]["fullTime"]
        half = m["score"]["halfTime"]
        rows.append((
            m["id"], int(m["season"]["startDate"][:4]), m["matchday"], m["status"],
            m["utcDate"], m["homeTeam"]["id"], m["awayTeam"]["id"],
            full["home"], full["away"], half["home"], half["away"],
            m["score"]["winner"], m["lastUpdated"],
        ))
    return rows


def standings_rows(raw, snapshot_date):
    season_year = int(raw["season"]["startDate"][:4])
    rows = []
    for block in raw["standings"]:
        for r in block["table"]:
            rows.append((
                snapshot_date, season_year, block["type"], r["position"],
                r["team"]["id"], r["playedGames"], r["won"], r["draw"], r["lost"],
                r["points"], r["goalsFor"], r["goalsAgainst"], r["goalDifference"],
            ))
    return rows


def scorers_rows(raw, snapshot_date):
    season_year = int(raw["season"]["startDate"][:4])
    return [
        (snapshot_date, season_year, s["player"]["id"], s["player"]["name"],
         s["player"].get("nationality"), s["player"].get("section"),
         s["team"]["id"], s.get("playedMatches"), s.get("goals"),
         s.get("assists"), s.get("penalties"))
        for s in raw["scorers"]
    ]