"""Quick API-key connectivity check. Run: python check_apis.py
Calls each API with the keys in .env and reports OK/FAIL without printing secrets."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TIMEOUT = 15


def check_tmdb() -> bool:
    key = os.getenv("TMDB_API_KEY")
    token = os.getenv("TMDB_API_READ_ACCESS_TOKEN")
    if token:  # prefer v4 bearer token
        r = requests.get(
            "https://api.themoviedb.org/3/movie/550",
            headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT,
        )
    elif key:
        r = requests.get(
            "https://api.themoviedb.org/3/movie/550",
            params={"api_key": key}, timeout=TIMEOUT,
        )
    else:
        print("skip  TMDB — no key set")
        return True
    if r.ok:
        print(f"ok    TMDB — fetched '{r.json()['title']}' ({r.json()['release_date'][:4]})")
        return True
    print(f"FAIL  TMDB — HTTP {r.status_code}: {r.json().get('status_message', r.text[:80])}")
    return False


def check_omdb() -> bool:
    key = os.getenv("OMDB_API_KEY")
    if not key:
        print("skip  OMDb — no key set")
        return True
    r = requests.get("https://www.omdbapi.com/",
                     params={"apikey": key, "i": "tt0137523"}, timeout=TIMEOUT)
    data = r.json()
    if r.ok and data.get("Response") == "True":
        print(f"ok    OMDb — fetched '{data['Title']}' (RT/IMDb available)")
        return True
    print(f"FAIL  OMDb — {data.get('Error', f'HTTP {r.status_code}')}")
    return False


def check_youtube() -> bool:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        print("skip  YouTube — no key set")
        return True
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"key": key, "q": "movie trailer", "part": "snippet", "maxResults": 1},
        timeout=TIMEOUT,
    )
    if r.ok:
        print("ok    YouTube Data API — search returned results")
        return True
    err = r.json().get("error", {}).get("message", r.text[:80])
    print(f"FAIL  YouTube — HTTP {r.status_code}: {err}")
    return False


if __name__ == "__main__":
    results = [check_tmdb(), check_omdb(), check_youtube()]
    print("\nall keys working" if all(results) else "\nsome keys failed — see above")
    raise SystemExit(0 if all(results) else 1)
