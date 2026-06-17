"""Shared UI chrome for every page: CSS, the top navigation, and the footer."""
import os
import streamlit as st

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# (label, url-path, key) — must match the url_path of each st.Page in app.py.
NAV = [
    ("Pulse",    "/",           "overview"),
    ("Critics",  "/critical",   "critical"),
    ("Hype",     "/hype",       "hype"),
    ("Genres",   "/genres",     "genres"),
    ("Pipeline", "/operations", "operations"),
    ("Weekly",   "/subscribe",  "subscribe"),
]


def favicon():
    return os.path.join(_ASSETS, "favicon64.png")


def inject_css():
    with open(os.path.join(_ASSETS, "style.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def header(active: str, subtitle: str = "analytics"):
    links = "".join(
        f'<a class="{ "active" if key == active else "" }" href="{url}" '
        f'target="_self">{label}</a>'
        for label, url, key in NAV
    )
    st.markdown(f"""
    <div id="top" class="fk-nav">
      <div class="fk-brand">
        <div class="fk-mark">F</div>
        <div>
          <span class="fk-word"><b>Flicker</b></span>
          <span class="fk-tag">{subtitle}</span>
        </div>
      </div>
      <div class="fk-links">
        {links}
        <span class="fk-pill"><span class="fk-dot"></span>Live · 3 sources</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def eyebrow(text: str):
    """Small uppercase gold label rendered above a hero headline."""
    return f'<div class="fk-eyebrow">{text}</div>'


def footer():
    st.markdown("""
    <div class="fk-foot">
      <span>Flicker · Film Intelligence</span>
      <span>DuckDB · dbt · Kafka · Streamlit · Data from
        <span class="gold">TMDB · OMDb · YouTube</span></span>
    </div>
    """, unsafe_allow_html=True)


def style_fig(fig, height: int = 330):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#9A9AAA", size=12.5),
        margin=dict(t=6, b=6, l=6, r=6), height=height, bargap=0.35,
        xaxis=dict(showgrid=False, color="#9A9AAA"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, color="#9A9AAA"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9A9AAA")),
        hoverlabel=dict(bgcolor="#1B1B23", bordercolor="rgba(255,255,255,0.12)",
                        font=dict(family="Inter", color="#ECECEF")),
    )
    return fig
