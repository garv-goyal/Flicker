"""Send the weekly Flicker newsletter to all active subscribers.

Usage:
    python newsletter/send_newsletter.py            # send to everyone
    python newsletter/send_newsletter.py --dry-run  # print first email, don't send
    python newsletter/send_newsletter.py --to me@example.com  # single address test

Subscriber table (created on first run):
    bronze.newsletter_subscribers (email, genre_pref, subscribed_at, active)
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

import duckdb
import resend
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from newsletter.recommendations import get_picks
from newsletter.email_template import build_email, subject_line

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "flicker.duckdb")

# Resend's built-in test address — works without domain verification.
# For production: verify a domain at resend.com/domains and change this.
FROM_ADDRESS = "Flicker Weekly <onboarding@resend.dev>"
REPLY_TO = "onboarding@resend.dev"

_SUBSCRIBER_DDL = """
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE TABLE IF NOT EXISTS bronze.newsletter_subscribers (
    email          TEXT        PRIMARY KEY,
    genre_pref     TEXT,
    subscribed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    active         BOOLEAN     NOT NULL DEFAULT true
);
"""


def _db_conn(read_only: bool = False):
    use_md = os.getenv("FLICKER_USE_MOTHERDUCK", "false").lower() == "true"
    if use_md:
        token = os.environ["MOTHERDUCK_TOKEN"]
        db_name = os.getenv("MOTHERDUCK_DATABASE", "flicker")
        return duckdb.connect(f"md:{db_name}?motherduck_token={token}")
    return duckdb.connect(os.getenv("FLICKER_DB_PATH", _DB_PATH), read_only=read_only)


def ensure_subscribers_table():
    conn = _db_conn()
    conn.execute(_SUBSCRIBER_DDL)
    conn.close()


def get_subscribers() -> list[dict]:
    conn = _db_conn(read_only=True)
    rows = conn.execute(
        "SELECT email, genre_pref FROM bronze.newsletter_subscribers WHERE active = true"
    ).fetchall()
    conn.close()
    return [{"email": r[0], "genre_pref": r[1]} for r in rows]


def send_to(email: str, genre_pref: str | None, dry_run: bool = False) -> bool:
    picks = get_picks(genre_pref)
    if picks["main_pick"] is None:
        print(f"  [skip] No picks available for genre={genre_pref!r}")
        return False

    html = build_email(picks, email, genre_pref)
    subj = subject_line(picks)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"TO:      {email}")
        print(f"FROM:    {FROM_ADDRESS}")
        print(f"SUBJECT: {subj}")
        print(f"{'='*60}")
        print(html[:2000] + "\n... [truncated]")
        return True

    resend.api_key = os.environ["RESEND_API_KEY"]
    params: resend.Emails.SendParams = {
        "from": FROM_ADDRESS,
        "to": [email],
        "reply_to": REPLY_TO,
        "subject": subj,
        "html": html,
    }
    response = resend.Emails.send(params)
    return bool(response.get("id"))


def main():
    ap = argparse.ArgumentParser(description="Send Flicker weekly newsletter")
    ap.add_argument("--dry-run", action="store_true", help="Print HTML, don't send")
    ap.add_argument("--to", metavar="EMAIL", help="Send to a single address (test mode)")
    args = ap.parse_args()

    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key and not args.dry_run:
        sys.exit("RESEND_API_KEY not set in environment")

    ensure_subscribers_table()

    if args.to:
        subscribers = [{"email": args.to, "genre_pref": None}]
    else:
        subscribers = get_subscribers()

    if not subscribers:
        print("No active subscribers. Add some via the Newsletter page on the web app.")
        return

    print(f"Sending to {len(subscribers)} subscriber(s) …")
    sent, failed = 0, 0
    for sub in subscribers:
        email = sub["email"]
        genre = sub["genre_pref"]
        try:
            ok = send_to(email, genre, dry_run=args.dry_run)
            if ok:
                sent += 1
                print(f"  ✓  {email}" + (f" [{genre}]" if genre else ""))
            else:
                failed += 1
                print(f"  ✗  {email} — no picks available")
        except Exception as exc:
            failed += 1
            print(f"  ✗  {email} — {exc}")
        if not args.dry_run and len(subscribers) > 1:
            time.sleep(0.5)  # stay well within Resend rate limits

    print(f"\nDone. {sent} sent, {failed} failed.")


if __name__ == "__main__":
    main()
