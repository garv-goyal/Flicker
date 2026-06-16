"""Overview (Industry Pulse) — page body. Rendered by app.py via st.navigation."""
import plotly.express as px
import streamlit as st

from utils import queries, ui


@st.cache_data(ttl=120)
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
    }


def money(v):
    return "—" if v is None else f"${v:,.0f}"


data = load()
m, roi = data["metrics"], data["roi"]

st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Industry overview")}
  <h1>What makes a film <em>succeed</em>?</h1>
  <p>Flicker analyses the <strong>{int(m.total_films):,} most popular films ever made</strong>
     — the titles audiences actually watch and that carry complete budget, revenue and
     review data — to surface the patterns behind box-office returns, critical reception
     and genre performance.</p>
</div>
<div class="fk-kpis">
  <div class="fk-kpi"><div class="v">{int(m.total_films):,}</div><div class="l">Top films analyzed</div></div>
  <div class="fk-kpi"><div class="v">{int(m.first_year)}–{int(m.last_year)}</div><div class="l">Year coverage</div></div>
  <div class="fk-kpi"><div class="v">{int(m.genres)}</div><div class="l">Genres tracked</div></div>
  <div class="fk-kpi"><div class="v">{roi.profitable_pct:.0f}%</div><div class="l">Profitable</div></div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([3, 2], gap="medium")

with left:
    st.markdown('<div class="fk-section"><h2>Return on investment by decade</h2>'
                '<p>Median ROI — resistant to outliers. Hover for averages.</p></div>',
                unsafe_allow_html=True)
    dec = data["decade"].copy()
    dec["Decade"] = dec["release_decade"].astype(int).astype(str) + "s"
    fig = px.bar(dec, x="Decade", y="median_roi",
                 custom_data=["film_count", "avg_roi", "profitable_pct"])
    fig.update_traces(marker_color="#E8B84B", marker_line_width=0,
                      hovertemplate="<b>%{x}</b><br>Median ROI: %{y}×<br>"
                      "Films: %{customdata[0]}<br>Avg ROI: %{customdata[1]}×<br>"
                      "Profitable: %{customdata[2]}%<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Median ROI (×)")
    with st.container(border=True):
        st.plotly_chart(ui.style_fig(fig), width="stretch",
                        config={"displayModeBar": False})

with right:
    st.markdown('<div class="fk-section"><h2>Most profitable genres</h2>'
                '<p>Genres with 10+ films, ranked by average ROI.</p></div>',
                unsafe_allow_html=True)
    rows = "".join(
        f'<tr><td class="rank">{i}</td><td class="title-cell">{g.primary_genre}</td>'
        f'<td class="num muted">{g.films}</td><td class="num gold">{g.avg_roi:.1f}×</td>'
        f'<td class="num muted">{g.avg_rating:.1f}</td></tr>'
        for i, g in enumerate(data["genres"].itertuples(), 1))
    st.markdown(f"""
    <div class="fk-card"><table class="fk-table">
      <thead><tr><th class="rank"></th><th>Genre</th><th class="num">Films</th>
        <th class="num">ROI</th><th class="num">Rating</th></tr></thead>
      <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

st.markdown('<div class="fk-section"><h2>Highest-ROI films of all time</h2>'
            '<p>Budget ≥ $1M, ranked by revenue ÷ budget.</p></div>',
            unsafe_allow_html=True)
rows = "".join(
    f'<tr><td class="rank">{i}</td><td class="title-cell">{f.title}</td>'
    f'<td class="muted num">{int(f.release_year)}</td>'
    f'<td><span class="fk-chip">{f.primary_genre}</span></td>'
    f'<td class="num muted">{money(f.budget_usd)}</td>'
    f'<td class="num">{money(f.revenue_usd)}</td>'
    f'<td class="num gold">{f.roi_ratio:,.1f}×</td>'
    f'<td class="num muted">{f.tmdb_rating:.1f}</td></tr>'
    for i, f in enumerate(data["top"].itertuples(), 1))
st.markdown(f"""
<div class="fk-card"><table class="fk-table">
  <thead><tr><th class="rank"></th><th>Title</th><th class="num">Year</th><th>Genre</th>
    <th class="num">Budget</th><th class="num">Revenue</th><th class="num">ROI</th>
    <th class="num">Rating</th></tr></thead>
  <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)

# --- Audience sentiment vs critics (streaming buzz → VADER → metric) ---------
bz = data["buzz_summary"]
scatter = data["buzz_scatter"]
st.markdown(f'<div class="fk-section"><h2>Audience sentiment vs critics '
            f'<span class="fk-chip">streaming</span></h2>'
            f'<p>{int(bz.scored):,} YouTube trailer comments across {int(bz.films)} films '
            f'are streamed through Kafka and scored with VADER sentiment. '
            f'{bz.pct_positive:.0f}% read as positive — but enthusiasm in the comments '
            f'barely tracks what critics think (r = {bz.corr_to_critics:.2f}).</p></div>',
            unsafe_allow_html=True)

if scatter is None or len(scatter) == 0:
    st.markdown('<div class="fk-card" style="padding:22px 18px;color:var(--muted)">'
                'No buzz yet — run the YouTube comments producer, consumer and '
                'sentiment scorer to stream trailer discussion into the warehouse.</div>',
                unsafe_allow_html=True)
else:
    sc = scatter.copy()
    fig = px.scatter(
        sc, x="critic_score", y="pct_positive",
        color="divergence", color_continuous_scale=["#F87171", "#9A9AAA", "#34D399"],
        range_color=[-70, 70], custom_data=["title", "release_year", "buzz_events"])
    fig.update_traces(marker=dict(size=10, line=dict(width=0)),
                      hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                      "Critic score: %{x}<br>Positive comments: %{y}%<br>"
                      "Comments: %{customdata[2]}<extra></extra>")
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                  line=dict(color="rgba(255,255,255,0.18)", width=1, dash="dot"))
    fig.update_layout(xaxis_title="Critic score (Rotten Tomatoes %)",
                      yaxis_title="Positive comments (%)", coloraxis_showscale=False,
                      xaxis_range=[0, 100], yaxis_range=[0, 100])
    with st.container(border=True):
        st.plotly_chart(ui.style_fig(fig, height=380), width="stretch",
                        config={"displayModeBar": False})
    st.markdown('<div class="fk-legend">'
                '<span><i style="background:#34D399"></i>Crowd warmer than critics</span>'
                '<span><i style="background:#F87171"></i>Critics warmer than crowd</span>'
                '<span>Dotted line = perfect agreement</span></div>',
                unsafe_allow_html=True)

    def gap_table(df, badge):
        rows = "".join(
            f'<tr><td class="title-cell">{r.title} '
            f'<span class="muted">{int(r.release_year)}</span></td>'
            f'<td class="num muted">{r.critic_score:.0f}</td>'
            f'<td class="num gold">{r.pct_positive:.0f}%</td>'
            f'<td class="num"><span class="badge {badge}">{r.divergence:+.0f}</span></td></tr>'
            for r in df.itertuples())
        head = ('<thead><tr><th>Film</th><th class="num">Critic</th>'
                '<th class="num">Crowd +</th><th class="num">Gap</th></tr></thead>')
        return (f'<div class="fk-card"><table class="fk-table">{head}'
                f'<tbody>{rows}</tbody></table></div>')

    gap_left, gap_right = st.columns(2, gap="medium")
    with gap_left:
        st.markdown('<div class="fk-section"><h2>Crowd loves more than critics</h2>'
                    '<p>Audiences far warmer than the reviews.</p></div>',
                    unsafe_allow_html=True)
        st.markdown(gap_table(data["crowd_fav"], "delivered"), unsafe_allow_html=True)
    with gap_right:
        st.markdown('<div class="fk-section"><h2>Critics rate higher than crowd</h2>'
                    '<p>Acclaim the comments didn\'t echo.</p></div>',
                    unsafe_allow_html=True)
        st.markdown(gap_table(data["critic_fav"], "overhyped"), unsafe_allow_html=True)
