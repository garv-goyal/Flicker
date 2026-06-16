"""Critical Reception — page body. Critic & audience scores, awards (OMDb data)."""
import pandas as pd
import streamlit as st

from utils import queries, ui


@st.cache_data(ttl=600)
def load():
    return {
        "summary": queries.critical_summary().iloc[0],
        "best": queries.best_reviewed(12),
        "audience_fav": queries.audience_over_critics(7),
        "critics_fav": queries.critics_over_audience(7),
    }


d = load()
s = d["summary"]

st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Critical reception")}
  <h1>The most <em>acclaimed</em> films</h1>
  <p>A composite score blends Rotten Tomatoes, Metacritic, IMDb and TMDB ratings
     onto a single 0–100 scale, so critic and audience opinion can be compared directly.</p>
</div>
<div class="fk-kpis">
  <div class="fk-kpi"><div class="v">{int(s.scored):,}</div><div class="l">Films scored</div></div>
  <div class="fk-kpi"><div class="v">{s.avg_composite:.0f}</div><div class="l">Avg composite</div></div>
  <div class="fk-kpi"><div class="v">{int(s.oscar_winners)}</div><div class="l">Oscar winners</div></div>
  <div class="fk-kpi"><div class="v">{int(s.with_rt):,}</div><div class="l">With RT score</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="fk-section"><h2>Best-reviewed films</h2>'
            '<p>Ranked by composite score across all four ratings sources. '
            'Awards shows Academy Award wins.</p></div>',
            unsafe_allow_html=True)


def cell(v, suffix=""):
    return "—" if pd.isna(v) else f"{v}{suffix}"


def awards_cell(f):
    """OMDb reliably names only the Academy Awards, so show the Oscar win count
    (the one unambiguous, specific award figure) rather than vague totals."""
    n = 0 if pd.isna(f.oscar_wins) else int(f.oscar_wins)
    if n >= 1:
        label = "Oscar" if n == 1 else "Oscars"
        return f'<span class="badge hidden">{n}× {label}</span>'
    return '<span class="muted">—</span>'


rows = ""
for i, f in enumerate(d["best"].itertuples(), 1):
    rows += (f'<tr><td class="rank">{i}</td><td class="title-cell">{f.title}</td>'
             f'<td class="muted num">{int(f.release_year)}</td>'
             f'<td><span class="fk-chip">{f.primary_genre}</span></td>'
             f'<td class="num gold">{f.composite_score:.0f}</td>'
             f'<td class="num muted">{cell(f.rt_score, "%")}</td>'
             f'<td class="num muted">{cell(f.metacritic_score)}</td>'
             f'<td class="num muted">{cell(f.imdb_rating)}</td>'
             f'<td>{awards_cell(f)}</td></tr>')
st.markdown(f"""
<div class="fk-card"><table class="fk-table">
  <thead><tr><th class="rank"></th><th>Title</th><th class="num">Year</th><th>Genre</th>
    <th class="num">Composite</th><th class="num">RT</th><th class="num">Metacritic</th>
    <th class="num">IMDb</th><th>Awards</th></tr></thead>
  <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

st.markdown('<div class="fk-section"><h2>Where critics and audiences disagree</h2>'
            '<p>Widest gaps between the critics\' score (Rotten Tomatoes) and the audience '
            'rating (TMDB), among films with broad critical coverage and 1,000+ votes.</p></div>',
            unsafe_allow_html=True)


def gap_table(df):
    rows = "".join(
        f'<tr><td class="title-cell">{r.title}</td>'
        f'<td class="muted num">{int(r.release_year)}</td>'
        f'<td class="num muted">{int(r.rt_score)}%</td>'
        f'<td class="num muted">{int(r.audience_score)}</td>'
        f'<td class="num gold">{int(r.gap)}</td></tr>'
        for r in df.itertuples())
    return (f'<div class="fk-card"><table class="fk-table"><thead><tr><th>Title</th>'
            f'<th class="num">Year</th><th class="num">Critics</th>'
            f'<th class="num">Audience</th><th class="num">Gap</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


left, right = st.columns(2, gap="medium")
with left:
    st.markdown('<div class="fk-section"><h2>Audiences loved them, critics didn\'t</h2>'
                '<p>Crowd-pleasers the critics panned.</p></div>', unsafe_allow_html=True)
    st.markdown(gap_table(d["audience_fav"]), unsafe_allow_html=True)
with right:
    st.markdown('<div class="fk-section"><h2>Critics loved them, audiences were cooler</h2>'
                '<p>Critical darlings that left audiences lukewarm.</p></div>',
                unsafe_allow_html=True)
    st.markdown(gap_table(d["critics_fav"]), unsafe_allow_html=True)
