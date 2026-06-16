"""Hype vs Reality — page body. Trailer buzz (YouTube) vs box-office return."""
import plotly.express as px
import streamlit as st

from utils import queries, ui

COLORS = {"Delivered": "#34D399", "Overhyped": "#F87171",
          "Hidden gem": "#E8B84B", "Overlooked": "#6B6B78"}


@st.cache_data(ttl=600)
def load():
    counts = queries.hype_counts().set_index("outcome_label")
    return {
        "scatter": queries.hype_scatter(),
        "counts": counts,
        "overhyped": queries.hype_examples("Overhyped", 6),
        "gems": queries.hype_examples("Hidden gem", 6),
        "sentiment": queries.buzz_vs_roi(),
        "sent_corr": queries.buzz_roi_corr().iloc[0],
    }


d = load()
c = d["counts"]


def n(label):
    return int(c.loc[label, "films"]) if label in c.index else 0


st.markdown(f"""
<div class="fk-hero">
  {ui.eyebrow("Hype vs reality")}
  <h1>Did the <em>hype</em> match reality?</h1>
  <p>Each film's trailer views (the buzz) plotted against its actual return on investment
     (the reality). Films are labelled by comparing both against the median of this set.</p>
</div>
<div class="fk-kpis">
  <div class="fk-kpi"><div class="v">{n('Delivered')}</div><div class="l">Delivered</div></div>
  <div class="fk-kpi"><div class="v">{n('Hidden gem')}</div><div class="l">Hidden gems</div></div>
  <div class="fk-kpi"><div class="v">{n('Overhyped')}</div><div class="l">Overhyped</div></div>
  <div class="fk-kpi"><div class="v">{n('Overlooked')}</div><div class="l">Overlooked</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="fk-section"><h2>Trailer buzz vs box-office return</h2>'
            '<p>Trailer views (log scale) against ROI. Top-right delivered; bottom-right overhyped.</p></div>',
            unsafe_allow_html=True)

sc = d["scatter"]
fig = px.scatter(sc, x="trailer_views", y="roi_ratio", color="outcome_label",
                 color_discrete_map=COLORS, log_x=True, log_y=True,
                 custom_data=["title", "release_year", "primary_genre"])
fig.update_traces(marker=dict(size=10, opacity=0.85, line=dict(width=0)),
                  hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                  "%{customdata[2]}<br>Trailer views: %{x:,}<br>ROI: %{y:.1f}×<extra></extra>")
fig.update_layout(xaxis_title="Trailer views", yaxis_title="ROI (×)", showlegend=False)
with st.container(border=True):
    st.plotly_chart(ui.style_fig(fig, height=420), width="stretch",
                    config={"displayModeBar": False})
st.markdown("""
<div class="fk-legend">
  <span><i style="background:#34D399"></i>Delivered — big buzz, strong return</span>
  <span><i style="background:#F87171"></i>Overhyped — big buzz, weak return</span>
  <span><i style="background:#E8B84B"></i>Hidden gem — quiet buzz, strong return</span>
  <span><i style="background:#6B6B78"></i>Overlooked — quiet buzz, weak return</span>
</div>
""", unsafe_allow_html=True)

left, right = st.columns(2, gap="medium")


def mini_table(df):
    rows = "".join(
        f'<tr><td class="title-cell">{r.title}</td>'
        f'<td class="muted num">{int(r.release_year)}</td>'
        f'<td class="num muted">{int(r.trailer_views):,}</td>'
        f'<td class="num gold">{r.roi_ratio:.1f}×</td></tr>'
        for r in df.itertuples())
    return (f'<div class="fk-card"><table class="fk-table"><thead><tr><th>Title</th>'
            f'<th class="num">Year</th><th class="num">Trailer views</th>'
            f'<th class="num">ROI</th></tr></thead><tbody>{rows}</tbody></table></div>')


with left:
    st.markdown('<div class="fk-section"><h2>Overhyped</h2>'
                '<p>Huge trailer buzz, underwhelming returns.</p></div>', unsafe_allow_html=True)
    st.markdown(mini_table(d["overhyped"]), unsafe_allow_html=True)

with right:
    st.markdown('<div class="fk-section"><h2>Hidden gems</h2>'
                '<p>Modest buzz, outsized returns.</p></div>', unsafe_allow_html=True)
    st.markdown(mini_table(d["gems"]), unsafe_allow_html=True)

# --- Audience sentiment vs return (streaming buzz → VADER → ROI) -------------
sent = d["sentiment"]
sc2 = d["sent_corr"]
st.markdown(f'<div class="fk-section"><h2>Does audience sentiment predict returns? '
            f'<span class="fk-chip">streaming</span></h2>'
            f'<p>Share of positive trailer comments (VADER sentiment, streamed via Kafka) '
            f'against box-office ROI for {int(sc2.films)} films. The relationship is '
            f'essentially flat (r = {sc2.corr_to_roi:.2f}) — enthusiasm in the comments '
            f'is not a reliable signal of commercial success.</p></div>',
            unsafe_allow_html=True)

if sent is not None and len(sent) > 0:
    ss = sent.copy()
    ss["Outcome"] = ss["is_profitable"].map({True: "Profitable", False: "Lost money"})
    fig2 = px.scatter(
        ss, x="pct_positive", y="roi_ratio", log_y=True, color="Outcome",
        color_discrete_map={"Profitable": "#34D399", "Lost money": "#F87171"},
        custom_data=["title", "release_year", "buzz_events"])
    fig2.update_traces(marker=dict(size=10, opacity=0.85, line=dict(width=0)),
                       hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                       "Positive comments: %{x}%<br>ROI: %{y:.1f}×<br>"
                       "Comments: %{customdata[2]}<extra></extra>")
    fig2.update_layout(xaxis_title="Positive trailer comments (%)",
                       yaxis_title="ROI (×, log scale)", showlegend=True,
                       legend=dict(orientation="h", y=1.08, x=0, title=None))
    with st.container(border=True):
        st.plotly_chart(ui.style_fig(fig2, height=400), width="stretch",
                        config={"displayModeBar": False})
    st.markdown('<div class="fk-legend">'
                '<span><i style="background:#34D399"></i>Turned a profit</span>'
                '<span><i style="background:#F87171"></i>Lost money</span>'
                '<span>Crowd-loved flops sit bottom-right; quiet earners sit top-left</span>'
                '</div>', unsafe_allow_html=True)
