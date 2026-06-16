"""Genre Trends — page body. How genres perform and grow over time."""
import plotly.express as px
import streamlit as st

from utils import queries, ui


@st.cache_data(ttl=600)
def load():
    return {"trends": queries.genre_year_trends(1990), "totals": queries.genre_totals()}


d = load()
totals = d["totals"]

st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Genre trends")}
  <h1>How genres <em>evolve</em></h1>
  <p>Output, ratings and returns by genre over time — which genres studios make more of,
     and which actually pay off.</p>
</div>
""", unsafe_allow_html=True)

top_genres = totals.sort_values("films", ascending=False)["primary_genre"].head(6).tolist()
chosen = st.multiselect("Genres", options=totals["primary_genre"].tolist(),
                        default=top_genres, label_visibility="collapsed")

st.markdown('<div class="fk-section"><h2>Films released per year</h2>'
            '<p>Annual output by genre since 1990.</p></div>', unsafe_allow_html=True)

trends = d["trends"]
view = trends[trends["primary_genre"].isin(chosen)] if chosen else trends
PALETTE = ["#E8B84B", "#E07A5F", "#5FA8A0", "#7A8CCB", "#C97FA6", "#8FB46A",
          "#D9A05B", "#6FB1C9"]
fig = px.area(view, x="release_year", y="film_count", color="primary_genre",
              color_discrete_sequence=PALETTE, custom_data=["primary_genre"])
fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>%{x}: %{y} films<extra></extra>")
fig.update_layout(xaxis_title=None, yaxis_title="Films", legend_title_text="")
with st.container(border=True):
    st.plotly_chart(ui.style_fig(fig, height=380), width="stretch",
                    config={"displayModeBar": False})

st.markdown('<div class="fk-section"><h2>Genre scorecard</h2>'
            '<p>All genres with 10+ films — output, returns, ratings and total revenue.</p></div>',
            unsafe_allow_html=True)
rows = ""
for i, g in enumerate(totals.itertuples(), 1):
    if not g.total_revenue:
        rev = "—"
    elif g.total_revenue >= 1e9:
        rev = f"${g.total_revenue/1e9:.1f}B"
    else:
        rev = f"${g.total_revenue/1e6:.1f}M"
    rows += (f'<tr><td class="rank">{i}</td><td class="title-cell">{g.primary_genre}</td>'
             f'<td class="num muted">{g.films}</td>'
             f'<td class="num gold">{g.avg_roi:.1f}×</td>'
             f'<td class="num muted">{g.avg_score:.0f}</td>'
             f'<td class="num">{rev}</td></tr>')
st.markdown(f"""
<div class="fk-card"><table class="fk-table">
  <thead><tr><th class="rank"></th><th>Genre</th><th class="num">Films</th>
    <th class="num">Avg ROI</th><th class="num">Avg score</th>
    <th class="num">Total revenue</th></tr></thead>
  <tbody>{rows}</tbody></table></div>""", unsafe_allow_html=True)
