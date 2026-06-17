"""Operations — page body. The theatrical run tracked live via change data capture.

A Postgres operational database holds one row per film in release; Debezium reads
every INSERT/UPDATE/DELETE off the write-ahead log and streams it through Kafka
into the warehouse. This page is rebuilt entirely from that change stream — the
current state and the change feed both come from CDC events, not batch snapshots.
"""
import html

import streamlit as st

from utils import queries, ui

STATUS_BADGE = {"Now Playing": "delivered", "Holdover": "hidden",
                "Leaving Soon": "overlooked", "Ended": "overhyped"}
OP_BADGE = {"insert": "delivered", "update": "hidden", "delete": "overhyped"}


@st.cache_data(ttl=60)
def load():
    return {
        "summary": queries.lifecycle_summary().iloc[0],
        "mix": queries.lifecycle_status_mix(),
        "current": queries.lifecycle_current(12),
        "changes": queries.lifecycle_changes(14),
    }



data = load()
s = data["summary"]

st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Operations · change data capture")}
  <h1>The theatrical run, <em>live</em></h1>
  <p>A Postgres operational database tracks every film's release — status, screen
     count, ticket price, weekend gross. <strong>Debezium</strong> captures each row
     change off the write-ahead log and streams it through Kafka into the warehouse,
     so this view is reconstructed entirely from the change stream — no batch polling.</p>
</div>
<div class="fk-kpis kpis-2">
  <div class="fk-kpi"><div class="v">{int(s.live_films)}</div><div class="l">Films in release</div></div>
  <div class="fk-kpi"><div class="v">{int(s.now_playing)}</div><div class="l">Now playing</div></div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([3, 2], gap="medium")

with left:
    st.markdown('<div class="fk-section"><h2>Now in release</h2>'
                '<p>Current state per film, rebuilt from the latest CDC event.</p></div>',
                unsafe_allow_html=True)
    rows = "".join(
        f'<tr><td class="title-cell">{html.escape(str(r.title))}</td>'
        f'<td><span class="badge {STATUS_BADGE.get(r.status, "overlooked")}">{r.status}</span></td>'
        f'<td class="num muted">{r.popularity:.1f}</td>'
        f'<td class="num muted">{int(r.vote_count):,}</td>'
        f'<td class="num gold">{r.vote_average:.1f}</td></tr>'
        for r in data["current"].itertuples())
    st.markdown(f"""
    <div class="fk-card"><table class="fk-table">
      <thead><tr><th>Title</th><th>Status</th><th class="num">Popularity</th>
        <th class="num">Votes</th><th class="num">Rating</th></tr></thead>
      <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

with right:
    st.markdown('<div class="fk-section"><h2>Change feed</h2>'
                '<p>Live INSERT / UPDATE / DELETE events off the WAL.</p></div>',
                unsafe_allow_html=True)
    items = []
    for c in data["changes"].itertuples():
        badge = OP_BADGE.get(c.op_label, "overlooked")
        if c.op_label == "update" and c.status_changed:
            detail = f'{c.before_status} → {c.after_status}'
        elif c.op_label == "update":
            detail = f'popularity {c.before_popularity:.1f} → {c.after_popularity:.1f}'
        elif c.op_label == "insert":
            detail = f'opened · {c.after_status}'
        else:
            detail = 'pulled from release'
        items.append(
            f'<div class="fk-comment"><span class="badge {badge}">{c.op_label}</span>'
            f'<span class="fk-comment-text">{html.escape(str(c.title))}</span>'
            f'<span class="fk-comment-author">{html.escape(detail)}</span></div>')
    if items:
        st.markdown(f'<div class="fk-card" style="padding:4px 0">{"".join(items)}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="fk-card" style="padding:16px 20px">'
                    '<span class="muted">No mutations yet — initial snapshot loaded. '
                    'Run the daily sync to generate real UPDATE / DELETE events.</span></div>',
                    unsafe_allow_html=True)
