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

# ── what's in each issue ───────────────────────────────────────────────────────
st.markdown("""
<div class="fk-features">
  <div class="fk-feature">
    <div class="fk-feature-num">01</div>
    <div>
      <div class="fk-feature-label">This week's pick</div>
      <div class="fk-feature-desc">One film, scored across TMDB rating, audience buzz
        and popularity trend. Genre-filtered if you have a preference set.</div>
    </div>
  </div>
  <div class="fk-feature">
    <div class="fk-feature-num">02</div>
    <div>
      <div class="fk-feature-label">Leaving soon</div>
      <div class="fk-feature-desc">The best-rated film in its final days in theaters.
        Catch it before it's gone.</div>
    </div>
  </div>
  <div class="fk-feature">
    <div class="fk-feature-num">03</div>
    <div>
      <div class="fk-feature-label">Critics vs audiences</div>
      <div class="fk-feature-desc">Where opinion diverges most — the films audiences
        love that critics underrated, and the ones critics championed that left
        audiences cold.</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── form + panel ──────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown('<div class="fk-section" style="margin-top:0;"><h2>Subscribe</h2>'
                '<p>Free, weekly, unsubscribe any time.</p></div>',
                unsafe_allow_html=True)

    with st.form("subscribe_form", clear_on_submit=False):
        email_input = st.text_input(
            "Email address",
            placeholder="you@example.com",
            help="Your email stays in the Flicker database and is never shared."
        )
        genre_input = st.selectbox(
            "Genre preference (optional)",
            GENRES,
            help="Your weekly pick will be filtered to this genre first. "
                 "Falls back to all genres if nothing qualifies."
        )
        submitted = st.form_submit_button("Subscribe", use_container_width=True)

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
                <div class="fk-card" style="padding:16px 20px;border-color:rgba(52,211,153,0.25);
                                             background:rgba(52,211,153,0.04);margin-top:12px;">
                  <span style="color:#34D399;font-weight:600;">You're in.</span>
                  <span class="muted" style="color:var(--muted);"> First email lands this Sunday.</span>
                  {f'<br><span style="color:var(--faint);font-size:13px;margin-top:4px;display:block;">Picks filtered for <strong style="color:var(--gold);">{genre_clean}</strong>.</span>' if genre_clean else ""}
                </div>""", unsafe_allow_html=True)
            elif result == "updated":
                st.markdown("""
                <div class="fk-card" style="padding:16px 20px;border-color:rgba(232,184,75,0.25);
                                             background:rgba(232,184,75,0.04);margin-top:12px;">
                  <span style="color:#E8B84B;font-weight:600;">Preferences updated.</span>
                  <span style="color:var(--muted);"> Changes take effect from the next send.</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="fk-card" style="padding:16px 20px;margin-top:12px;">
                  <span style="color:var(--muted);">You're already subscribed with those preferences.</span>
                </div>""", unsafe_allow_html=True)

    st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
    with st.expander("Unsubscribe"):
        with st.form("unsubscribe_form", clear_on_submit=True):
            unsub_email = st.text_input("Email address to remove", placeholder="you@example.com")
            unsub_btn = st.form_submit_button("Unsubscribe", use_container_width=True)
        if unsub_btn:
            unsub_clean = unsub_email.strip().lower()
            if _is_valid_email(unsub_clean):
                _unsubscribe(unsub_clean)
                st.success(f"{unsub_clean} removed.")
            else:
                st.error("Enter a valid email address.")

with right:
    st.markdown("""
    <div class="fk-section" style="margin-top:0;"><h2>What you'll get</h2></div>
    <div class="fk-card" style="padding:22px 24px;">
      <div class="fk-content-item">
        <div class="fk-content-label">Main pick</div>
        <div class="fk-content-desc">One film scored on TMDB rating, audience buzz and
          popularity. Genre-filtered first if you set a preference, then all genres.</div>
      </div>
      <div class="fk-content-item">
        <div class="fk-content-label">Leaving soon</div>
        <div class="fk-content-desc">The best-rated film entering its final week in
          theaters. Catch it before it leaves.</div>
      </div>
      <div class="fk-content-item">
        <div class="fk-content-label">Critics vs crowds</div>
        <div class="fk-content-desc">Where audience sentiment diverges most from
          critic scores — the underrated gems and the overhyped ones.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
