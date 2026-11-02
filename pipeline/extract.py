import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.football-data.org/v4"
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

# PL is the Premier League code
COMPETITION = "PL"

# scorers may not be on the free tier, the script reports it and moves on
ENDPOINTS = {
    "teams": "teams",
    "matches": "matches",
    "standings": "standings",
    "scorers": "scorers?limit=50",
}

# call the API with the key in the header
def fetch(path):
    response = requests.get(
        f"{API_BASE}{path}",
        headers={"X-Auth-Token": API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

# save the untouched response so we can reprocess it later
def save_raw(name, data):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RAW_DIR / f"football_data_{COMPETITION}_{name}_{stamp}.json"
    path.write_text(json.dumps(data, indent=2))
    return path

# the run fails if any of these cannot be fetched
REQUIRED = {"teams", "matches", "standings"}

def extract_all():
    failed = []
    for name, endpoint in ENDPOINTS.items():
        try:
            data = fetch(f"/competitions/{COMPETITION}/{name}")
            path = save_raw(name, data)
            print(f"saved {name} -> {path.name}")
        except requests.HTTPError as e:
            print(f"skipped {name}: {e}")
            if name in REQUIRED:
                failed.append(name)
        # free tier allows 10 requests per minute, so wait between calls
        time.sleep(7)
    missing = REQUIRED & set(failed)
    if missing:
        raise RuntimeError(f"required endpoints failed: {sorted(missing)}")


if __name__ == "__main__":
    extract_all()