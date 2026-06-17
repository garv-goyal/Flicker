"""Overview (Pulse) — page body."""
import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import queries, ui


@st.cache_data(ttl=3600)
def load():
    return {
        "metrics": queries.headline_metrics().iloc[0],
        "roi": queries.roi_summary().iloc[0],
        "decade": queries.roi_by_decade(),
        "top": queries.top_roi_films(10),
        "genres": queries.genre_leaderboard(),
        "buzz_summary": queries.buzz_sentiment_summary().iloc[0],
        "buzz_scatter": queries.buzz_vs_critics(),
        "crowd_fav": queries.buzz_divergence("crowd", 5),
        "critic_fav": queries.buzz_divergence("critics", 5),
        "fotd": queries.film_of_the_day(),
    }


def money(v):
    return "—" if v is None else f"${v:,.0f}"


data = load()
m, roi = data["metrics"], data["roi"]

st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Industry pulse")}
  <h1>Film intelligence, <em>not guesswork</em></h1>
  <p>Box office returns, critic scores, and audience sentiment across {int(m.total_films):,} films —
     surfaced as patterns. See what works, what flops, and where the market is moving.</p>
</div>
<div class="fk-kpis">
  <div class="fk-kpi"><div class="v">{int(m.total_films):,}</div><div class="l">Films tracked</div></div>
  <div class="fk-kpi"><div class="v">{int(m.first_year)}–{int(m.last_year)}</div><div class="l">Year range</div></div>
  <div class="fk-kpi"><div class="v">{int(m.genres)}</div><div class="l">Genres</div></div>
  <div class="fk-kpi"><div class="v">{roi.profitable_pct:.0f}%</div><div class="l">Turned a profit</div></div>
</div>
""", unsafe_allow_html=True)

# ── Today's Pick ──────────────────────────────────────────────────────────────
fotd = data["fotd"]
if len(fotd) > 0:
    idx = datetime.date.today().timetuple().tm_yday % len(fotd)
    film = fotd.iloc[idx]

    def _safe(val):
        return None if pd.isna(val) else val

    composite = _safe(film.composite_score)
    rt        = _safe(film.rt_score)
    tmdb_pct  = None if _safe(film.tmdb_rating) is None else film.tmdb_rating * 10

    bars = ""
    for label, val in [("Composite", composite), ("Rotten Tomatoes", rt), ("Audience (TMDB)", tmdb_pct)]:
        if val is not None:
            bars += (
                f'<div class="fk-score-bar">'
                f'<span class="fk-score-label">{label}</span>'
                f'<div class="fk-score-track">'
                f'<div class="fk-score-fill" style="width:{min(val, 100):.0f}%"></div>'
                f'</div>'
                f'<span class="fk-score-value">{val:.0f}</span>'
                f'</div>'
            )

    roi_val     = _safe(film.roi_ratio)
    oscar_won   = _safe(film.won_oscar)
    oscar_wins  = _safe(film.oscar_wins)

    roi_text = (
        f"Returned <strong style='color:var(--gold)'>{roi_val:.1f}×</strong> "
        f"its budget at the box office." if roi_val else ""
    )
    oscar_text = ""
    if oscar_won:
        n = int(oscar_wins) if oscar_wins else 1
        oscar_text = f"<br>Won {n} {'Oscar' if n == 1 else 'Oscars'}."

    st.markdown(
        '<div class="fk-section" style="margin-top:36px;">'
        "<h2>Today's pick</h2>"
        "<p>One highly-rated film, rotated daily from the top of the dataset.</p></div>",
        unsafe_allow_html=True,
    )

    f_left, f_right = st.columns([3, 2], gap="medium")
    with f_left:
        st.markdown(f"""
        <div class="fk-film-feature">
          <div class="fk-film-date">{datetime.date.today().strftime("%B %d, %Y")}</div>
          <div class="fk-film-title">{film.title}</div>
          <div class="fk-film-meta">{int(film.release_year)}&ensp;·&ensp;{film.primary_genre}</div>
          <div class="fk-score-bars">{bars}</div>
        </div>
        """, unsafe_allow_html=True)
    with f_right:
        st.markdown(f"""
        <div class="fk-insight" style="height:100%;box-sizing:border-box;">
          <div class="fk-insight-label">Why this film</div>
          <p class="fk-insight-text">"{film.title}" ranks among the highest-rated films
            across all four scoring sources in the dataset.</p>
          <p class="fk-insight-sub">{roi_text}{oscar_text}</p>
        </div>
        """, unsafe_allow_html=True)

# ── ROI by decade + genre leaderboard ─────────────────────────────────────────
left, right = st.columns([3, 2], gap="medium")

with left:
    st.markdown('<div class="fk-section"><h2>ROI by decade</h2>'
                '<p>Median return on investment per decade. Resistant to outliers.</p></div>',
                unsafe_allow_html=True)
    dec = data["decade"].copy()
    dec["Decade"] = dec["release_decade"].astype(int).astype(str) + "s"
    fig = px.bar(dec, x="Decade", y="median_roi",
                 custom_data=["film_count", "avg_roi", "profitable_pct"])
    fig.update_traces(
        marker_color="#E8B84B", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Median ROI: %{y}×<br>"
                      "Films: %{customdata[0]}<br>Avg ROI: %{customdata[1]}×<br>"
                      "Profitable: %{customdata[2]}%<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, yaxis_title="Median ROI (×)")
    with st.container(border=True):
        st.plotly_chart(ui.style_fig(fig), width="stretch", config={"displayModeBar": False})

with right:
    st.markdown('<div class="fk-section"><h2>Highest-ROI genres</h2>'
                '<p>Genres with 10+ films, ranked by average return.</p></div>',
                unsafe_allow_html=True)
    rows = "".join(
        f'<tr><td class="rank">{i}</td><td class="title-cell">{g.primary_genre}</td>'
        f'<td class="num muted">{g.films}</td><td class="num gold">{g.avg_roi:.1f}×</td>'
        f'<td class="num muted">{g.avg_rating:.1f}</td></tr>'
        for i, g in enumerate(data["genres"].itertuples(), 1)
    )
    st.markdown(f"""
    <div class="fk-card"><table class="fk-table">
      <thead><tr><th class="rank"></th><th>Genre</th><th class="num">Films</th>
        <th class="num">ROI</th><th class="num">Rating</th></tr></thead>
      <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

# ── Key finding callout ────────────────────────────────────────────────────────
best = data["genres"].iloc[0] if len(data["genres"]) > 0 else None
if best is not None:
    st.markdown(f"""
    <div class="fk-insight">
      <div class="fk-insight-label">Key finding</div>
      <p class="fk-insight-text">{best.primary_genre} films average
        <strong style="color:var(--gold);font-style:normal;">{best.avg_roi:.1f}×</strong>
        return on budget — the highest of any genre in the dataset.</p>
      <p class="fk-insight-sub">Across {int(best.films)} films with verified budget and revenue data,
        the pattern holds even after removing outlier blockbusters.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Highest-return films ───────────────────────────────────────────────────────
st.markdown('<div class="fk-section"><h2>Highest-return films</h2>'
            '<p>Budget ≥ $1M. Ranked by revenue ÷ budget.</p></div>',
            unsafe_allow_html=True)
rows = "".join(
    f'<tr><td class="rank">{i}</td><td class="title-cell">{f.title}</td>'
    f'<td class="muted num">{int(f.release_year)}</td>'
    f'<td><span class="fk-chip">{f.primary_genre}</span></td>'
    f'<td class="num muted">{money(f.budget_usd)}</td>'
    f'<td class="num">{money(f.revenue_usd)}</td>'
    f'<td class="num gold">{f.roi_ratio:,.1f}×</td>'
    f'<td class="num muted">{f.tmdb_rating:.1f}</td></tr>'
    for i, f in enumerate(data["top"].itertuples(), 1)
)
st.markdown(f"""
<div class="fk-card"><table class="fk-table">
  <thead><tr><th class="rank"></th><th>Title</th><th class="num">Year</th><th>Genre</th>
    <th class="num">Budget</th><th class="num">Revenue</th><th class="num">ROI</th>
    <th class="num">Rating</th></tr></thead>
  <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

# ── Audience sentiment vs critics ──────────────────────────────────────────────
bz      = data["buzz_summary"]
scatter = data["buzz_scatter"]

st.markdown(
    f'<div class="fk-section"><h2>Audience sentiment vs critics '
    f'<span class="fk-chip">streaming</span></h2>'
    f'<p>{int(bz.scored):,} YouTube trailer comments across {int(bz.films)} films — '
    f'scored with VADER sentiment analysis. {bz.pct_positive:.0f}% positive, '
    f'with a weak correlation to critic scores (r = {bz.corr_to_critics:.2f}).</p></div>',
    unsafe_allow_html=True,
)

if scatter is None or len(scatter) == 0:
    st.markdown(
        '<div class="fk-card" style="padding:22px 18px;color:var(--muted)">'
        'No sentiment data yet — run the YouTube producer, consumer and scorer '
        'to stream trailer comments into the warehouse.</div>',
        unsafe_allow_html=True,
    )
else:
    sc = scatter.copy()
    fig = px.scatter(
        sc, x="critic_score", y="pct_positive",
        color="divergence", color_continuous_scale=["#F87171", "#8E90A8", "#34D399"],
        range_color=[-70, 70], custom_data=["title", "release_year", "buzz_events"],
    )
    fig.update_traces(
        marker=dict(size=9, line=dict(width=0)),
        hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                      "Critic score: %{x}<br>Positive comments: %{y}%<br>"
                      "Comments: %{customdata[2]}<extra></extra>",
    )
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                  line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"))
    fig.update_layout(
        xaxis_title="Critic score (RT %)", yaxis_title="Positive comments (%)",
        coloraxis_showscale=False, xaxis_range=[0, 100], yaxis_range=[0, 100],
    )
    with st.container(border=True):
        st.plotly_chart(ui.style_fig(fig, height=380), width="stretch",
                        config={"displayModeBar": False})
    st.markdown(
        '<div class="fk-legend">'
        '<span><i style="background:#34D399"></i>Audiences warmer than critics</span>'
        '<span><i style="background:#F87171"></i>Critics warmer than audiences</span>'
        '<span>Dotted line = perfect agreement</span></div>',
        unsafe_allow_html=True,
    )

    def gap_table(df, badge):
        rows = "".join(
            f'<tr><td class="title-cell">{r.title} '
            f'<span class="muted">{int(r.release_year)}</span></td>'
            f'<td class="num muted">{r.critic_score:.0f}</td>'
            f'<td class="num gold">{r.pct_positive:.0f}%</td>'
            f'<td class="num"><span class="badge {badge}">{r.divergence:+.0f}</span></td></tr>'
            for r in df.itertuples()
        )
        head = (
            '<thead><tr><th>Film</th><th class="num">Critics</th>'
            '<th class="num">Audiences</th><th class="num">Gap</th></tr></thead>'
        )
        return (f'<div class="fk-card"><table class="fk-table">{head}'
                f'<tbody>{rows}</tbody></table></div>')

    gap_left, gap_right = st.columns(2, gap="medium")
    with gap_left:
        st.markdown('<div class="fk-section"><h2>Audiences rate higher</h2>'
                    '<p>Where crowd sentiment ran warmer than the reviews.</p></div>',
                    unsafe_allow_html=True)
        st.markdown(gap_table(data["crowd_fav"], "delivered"), unsafe_allow_html=True)
    with gap_right:
        st.markdown('<div class="fk-section"><h2>Critics rate higher</h2>'
                    '<p>Where the reviews ran warmer than the crowd.</p></div>',
                    unsafe_allow_html=True)
        st.markdown(gap_table(data["critic_fav"], "overhyped"), unsafe_allow_html=True)
