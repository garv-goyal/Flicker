"""Subscribe — newsletter sign-up page."""
import re

import streamlit as st

from utils import ui
from utils.duckdb_conn import get_connection

GENRES = ["No preference", "Action", "Comedy", "Drama", "Horror",
          "Sci-Fi", "Thriller", "Family", "Animation", "Romance"]

_DDL = """
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE TABLE IF NOT EXISTS bronze.newsletter_subscribers (
    email          TEXT        PRIMARY KEY,
    genre_pref     TEXT,
    subscribed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    active         BOOLEAN     NOT NULL DEFAULT true
);
"""


def _ensure_table():
    conn = get_connection(read_only=False)
    conn.execute(_DDL)
    conn.close()


def _subscribe(email: str, genre: str | None) -> str:
    """Returns 'new', 'updated', or 'exists'."""
    conn = get_connection(read_only=False)
    existing = conn.execute(
        "SELECT active, genre_pref FROM bronze.newsletter_subscribers WHERE email = ?",
        [email]
    ).fetchone()
    if existing:
        active, old_genre = existing
        if active and old_genre == genre:
            conn.close()
            return "exists"
        conn.execute(
            "UPDATE bronze.newsletter_subscribers SET active=true, genre_pref=? WHERE email=?",
            [genre, email]
        )
        conn.close()
        return "updated"
    conn.execute(
        "INSERT INTO bronze.newsletter_subscribers (email, genre_pref) VALUES (?, ?)",
        [email, genre]
    )
    conn.close()
    return "new"


def _unsubscribe(email: str):
    conn = get_connection(read_only=False)
    conn.execute(
        "UPDATE bronze.newsletter_subscribers SET active=false WHERE email=?",
        [email]
    )
    conn.close()


def _is_valid_email(s: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s.strip()))


_ensure_table()

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Flicker · Weekly newsletter")}
  <h1>What to watch <em>this weekend</em></h1>
  <p>Every Sunday, Flicker queries real theater data — popularity trends, TMDB
     ratings, audience sentiment vs critic scores — and builds a data-backed
     recommendation just for you. No guesswork, no sponsored picks.</p>
</div>
""", unsafe_allow_html=True)

# ── what's inside ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="fk-kpis" style="margin-bottom:32px;">
  <div class="fk-kpi">
    <div class="v" style="font-size:20px;">🎬</div>
    <div class="l">This week's pick</div>
    <div class="muted" style="font-size:12px;margin-top:4px;">Scored on rating + buzz + popularity</div>
  </div>
  <div class="fk-kpi">
    <div class="v" style="font-size:20px;">⏳</div>
    <div class="l">Leaving soon</div>
    <div class="muted" style="font-size:12px;margin-top:4px;">Best-rated film in its final days</div>
  </div>
  <div class="fk-kpi">
    <div class="v" style="font-size:20px;">📊</div>
    <div class="l">Critics vs Crowds</div>
    <div class="muted" style="font-size:12px;margin-top:4px;">Where the biggest disagreements are</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── form ──────────────────────────────────────────────────────────────────────
left, _, right = st.columns([5, 1, 4])

with left:
    st.markdown('<div class="fk-section"><h2>Subscribe</h2>'
                '<p>Free, weekly, unsubscribe any time.</p></div>',
                unsafe_allow_html=True)

    with st.form("subscribe_form", clear_on_submit=False):
        email_input = st.text_input(
            "Email address",
            placeholder="you@example.com",
            help="Your email stays in the local Flicker database and is never shared."
        )
        genre_input = st.selectbox(
            "Genre preference (optional)",
            GENRES,
            help="Your weekly pick will be filtered to this genre first. "
                 "Falls back to all genres if nothing qualifies."
        )
        submitted = st.form_submit_button("Subscribe →", width="stretch")

    if submitted:
        email_clean = email_input.strip().lower()
        genre_clean = None if genre_input == "No preference" else genre_input

        if not email_clean:
            st.error("Please enter an email address.")
        elif not _is_valid_email(email_clean):
            st.error("That doesn't look like a valid email address.")
        else:
            result = _subscribe(email_clean, genre_clean)
            if result == "new":
                st.markdown(f"""
                <div class="fk-card" style="padding:16px 20px;border:1px solid rgba(52,211,153,0.25);
                                             background:rgba(52,211,153,0.05);margin-top:12px;">
                  <span style="color:#34D399;font-weight:600;">You're in.</span>
                  <span class="muted"> First email lands this Sunday.</span>
                  {f'<br><span class="muted" style="font-size:13px;">Picks will be filtered for <strong style="color:var(--gold);">{genre_clean}</strong>.</span>' if genre_clean else ""}
                </div>""", unsafe_allow_html=True)
            elif result == "updated":
                st.markdown("""
                <div class="fk-card" style="padding:16px 20px;border:1px solid rgba(232,184,75,0.25);
                                             background:rgba(232,184,75,0.05);margin-top:12px;">
                  <span style="color:#E8B84B;font-weight:600;">Preferences updated.</span>
                  <span class="muted"> Changes take effect from the next send.</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="fk-card" style="padding:16px 20px;margin-top:12px;">
                  <span class="muted">You're already subscribed with those preferences.</span>
                </div>""", unsafe_allow_html=True)

    # Unsubscribe section
    st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
    with st.expander("Unsubscribe"):
        with st.form("unsubscribe_form", clear_on_submit=True):
            unsub_email = st.text_input("Email address to remove", placeholder="you@example.com")
            unsub_btn = st.form_submit_button("Unsubscribe", width="stretch")
        if unsub_btn:
            unsub_clean = unsub_email.strip().lower()
            if _is_valid_email(unsub_clean):
                _unsubscribe(unsub_clean)
                st.success(f"{unsub_clean} removed from the list.")
            else:
                st.error("Enter a valid email address.")

with right:
    st.markdown("""
    <div class="fk-section"><h2>What you'll get</h2></div>
    <div class="fk-card" style="padding:20px 24px;">

      <div style="margin-bottom:16px;">
        <div style="color:var(--gold);font-size:12px;letter-spacing:1.5px;
                    text-transform:uppercase;font-weight:600;margin-bottom:4px;">
          Main Pick
        </div>
        <div style="color:var(--text);font-size:14px;line-height:1.6;">
          One film, scored on TMDB rating + audience buzz + popularity. If you set
          a genre, your pick comes from that genre first.
        </div>
      </div>

      <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:16px;"></div>

      <div style="margin-bottom:16px;">
        <div style="color:var(--red);font-size:12px;letter-spacing:1.5px;
                    text-transform:uppercase;font-weight:600;margin-bottom:4px;">
          Leaving Soon
        </div>
        <div style="color:var(--text);font-size:14px;line-height:1.6;">
          The best-rated film in its final days. Catch it before it's gone.
        </div>
      </div>

      <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:16px;"></div>

      <div>
        <div style="color:#9A9AAA;font-size:12px;letter-spacing:1.5px;
                    text-transform:uppercase;font-weight:600;margin-bottom:4px;">
          Critics vs Crowds
        </div>
        <div style="color:var(--text);font-size:14px;line-height:1.6;">
          Where audience sentiment diverges most from critic scores — the underrated
          gems and the overhyped ones.
        </div>
      </div>

    </div>
    """, unsafe_allow_html=True)
