"""Floating Text-to-SQL chatbot for the Flicker dashboard.

CCv2 component injects the button + panel onto document.body so it survives
Streamlit reruns and floats over every page. Python side calls Claude to
convert natural language → SQL → DuckDB results.
"""
import html
import os
import re
import textwrap

from google import genai
from google.genai import types
import streamlit as st
import streamlit.components.v2 as stv2
from dotenv import load_dotenv

from utils.duckdb_conn import get_connection

load_dotenv()

# ── Schema prompt ─────────────────────────────────────────────────────────────
_SCHEMA = """
Available DuckDB tables (Gold layer, schema prefix required):

gold.mart_film_lifecycle_current  — films currently in theaters
  tmdb_id INT, title TEXT, status TEXT ('Now Playing'|'Holdover'|'Leaving Soon'),
  popularity DOUBLE, vote_count INT, vote_average DOUBLE,
  primary_genre TEXT, release_year INT, last_change_ts TIMESTAMP

gold.mart_buzz_vs_critics  — audience sentiment vs critic scores
  tmdb_id INT, title TEXT, primary_genre TEXT, release_year INT,
  buzz_events INT, scored_events INT, avg_sentiment DOUBLE,
  pct_positive DOUBLE (% positive trailer comments),
  pct_negative DOUBLE, critic_score DOUBLE (Rotten Tomatoes %),
  composite_score DOUBLE, tmdb_rating DOUBLE, roi_ratio DOUBLE,
  divergence DOUBLE  (pct_positive − critic_score; positive = crowd warmer)

gold.mart_genre_trends  — genre performance by year (PRE-AGGREGATED: one row per genre+year, do NOT add GROUP BY)
  primary_genre TEXT, release_year INT, film_count INT,
  avg_budget_usd DOUBLE, avg_revenue_usd DOUBLE, avg_roi DOUBLE,
  avg_tmdb_rating DOUBLE, avg_popularity DOUBLE

gold.fact_title_performance  — financial + critical metrics per film
  title_key TEXT, budget_usd DOUBLE, revenue_usd DOUBLE,
  roi_ratio DOUBLE, is_profitable BOOLEAN,
  tmdb_rating DOUBLE, tmdb_vote_count INT,
  rt_score DOUBLE, metacritic_score DOUBLE, imdb_rating DOUBLE,
  composite_score DOUBLE, trailer_views INT, trailer_engagement DOUBLE,
  won_oscar BOOLEAN, oscar_wins INT, total_award_wins INT, popularity_score DOUBLE

gold.dim_titles  — title dimension (join key to fact_title_performance)
  title_key TEXT, tmdb_id INT, title TEXT,
  release_date DATE, release_year INT, release_decade INT,
  primary_genre TEXT, runtime_minutes INT,
  original_language TEXT, is_franchise BOOLEAN, collection_name TEXT

gold.mart_hype_vs_revenue  — trailer hype vs box-office reality
  title TEXT, release_year INT, primary_genre TEXT,
  budget_usd DOUBLE, revenue_usd DOUBLE, roi_ratio DOUBLE,
  trailer_views INT, trailer_engagement DOUBLE, composite_score DOUBLE,
  outcome_label TEXT ('Overhyped'|'Hidden gem'|'Delivered'|'Overlooked')

Join keys:
  dim_titles.title_key = fact_title_performance.title_key
  dim_titles.tmdb_id   = mart_film_lifecycle_current.tmdb_id
                       = mart_buzz_vs_critics.tmdb_id
"""

_SYSTEM = textwrap.dedent(f"""
You are Flicker's data assistant. Users ask natural-language questions about film analytics.

{_SCHEMA}

Rules:
1. Start with a clear, friendly 1–3 sentence answer. Use **bold** for film titles and key stats.
2. If data is needed, emit exactly one DuckDB SQL query in a ```sql fence.
   - Always prefix tables with their schema (gold.dim_titles, not dim_titles).
   - LIMIT results to 10 rows unless the user asks for more.
   - Only SELECT queries — never DDL or DML.
   - Always alias technical column names in your SELECT:
     roi_ratio AS "ROI", budget_usd AS "Budget", revenue_usd AS "Revenue",
     tmdb_rating AS "Rating", vote_count AS "Votes", primary_genre AS "Genre",
     release_year AS "Year", pct_positive AS "Positive %", pct_negative AS "Negative %",
     critic_score AS "Critics (RT%)", composite_score AS "Composite",
     film_count AS "Films", trailer_views AS "Trailer Views", avg_roi AS "ROI",
     avg_tmdb_rating AS "Avg Rating"
3. If the question needs no data (e.g. "what can you do?"), skip the SQL block.
4. Write conversationally. Mention the most interesting insight in your text. Bold standout figures.
5. Tables prefixed with mart_ are pre-aggregated. Query them with simple SELECT + ORDER BY + LIMIT — never add GROUP BY on mart_ tables.
""").strip()


def _extract_sql(text: str) -> str | None:
    m = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


_COL_PRETTY = {
    "roi_ratio": "ROI (×)", "avg_roi": "ROI (×)", "roi": "ROI (×)",
    "budget_usd": "Budget", "revenue_usd": "Revenue",
    "avg_budget_usd": "Avg Budget", "avg_revenue_usd": "Avg Revenue",
    "tmdb_rating": "Rating", "vote_average": "Rating",
    "tmdb_vote_count": "Votes", "vote_count": "Votes",
    "rt_score": "RT Score", "metacritic_score": "Metacritic",
    "imdb_rating": "IMDb", "composite_score": "Composite",
    "avg_tmdb_rating": "Avg Rating",
    "pct_positive": "Positive %", "pct_negative": "Negative %",
    "critic_score": "Critics (RT%)", "divergence": "Gap",
    "trailer_views": "Trailer Views", "primary_genre": "Genre",
    "release_year": "Year", "film_count": "Films",
    "avg_popularity": "Avg Popularity", "popularity_score": "Popularity",
    "buzz_events": "Buzz Events", "outcome_label": "Category",
    "is_profitable": "Profitable", "won_oscar": "Oscar Win",
    "oscar_wins": "Oscars", "total_award_wins": "Awards",
    "original_language": "Language", "runtime_minutes": "Runtime (min)",
}


def _prettify_col(col: str) -> str:
    return _COL_PRETTY.get(col.lower(), col.replace("_", " ").title())


def _fmt_cell(col: str, val) -> str:
    if val is None:
        return '<span style="color:#6B6B78">—</span>'
    if isinstance(val, bool):
        return "Yes" if val else "No"
    c = col.lower()

    # ROI → X,XXX.X×
    if "roi" in c:
        try:
            return f"{float(val):,.1f}×"
        except (TypeError, ValueError):
            pass

    # Money → compact $X.XB / $X.XM
    if any(x in c for x in ("budget", "revenue", "gross")):
        try:
            v = float(val)
            if v == 0:
                return '<span style="color:#6B6B78">—</span>'
            return f"${v/1e9:.1f}B" if abs(v) >= 1e9 else f"${v/1e6:.1f}M" if abs(v) >= 1e6 else f"${v:,.0f}"
        except (TypeError, ValueError):
            pass

    # Percentage / score columns
    if any(x in c for x in ("pct_positive", "pct_negative", "critic_score", "positive", "negative", "critics")):
        try:
            return f"{float(val):.0f}%"
        except (TypeError, ValueError):
            pass

    # Count/integer columns → comma-separated
    if any(x in c for x in ("vote_count", "votes", "film_count", "films", "trailer_views",
                              "buzz_events", "scored_events", "oscar_wins", "awards", "count")):
        try:
            return f"{int(val):,}"
        except (TypeError, ValueError):
            pass

    # Generic float
    if isinstance(val, float):
        return f"{val:,.1f}" if abs(val) >= 100 else f"{val:.2f}"

    # Generic int
    if isinstance(val, int):
        return f"{val:,}"

    return html.escape(str(val))


def _render_text(plain: str) -> str:
    """Convert Gemini plain text → safe HTML with light formatting."""
    escaped = html.escape(plain)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = escaped.replace("\n", "<br>")
    return escaped


def _run_sql(sql: str) -> tuple[list[str], list[tuple]]:
    conn = get_connection(read_only=True)
    try:
        rel = conn.execute(sql)
        cols = [d[0] for d in rel.description]
        rows = rel.fetchall()
        return cols, rows
    finally:
        conn.close()


def _table_html(cols: list[str], rows: list[tuple]) -> str:
    pretty = [_prettify_col(c) for c in cols]
    header = "".join(f"<th>{html.escape(p)}</th>" for p in pretty)
    body = "".join(
        "<tr>" + "".join(
            f"<td>{_fmt_cell(cols[i], v)}</td>"
            for i, v in enumerate(row)
        ) + "</tr>"
        for row in rows
    )
    count = f"{len(rows)} row{'s' if len(rows) != 1 else ''}"
    return (
        f'<div class="fk-sql-result">'
        f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
        f'<div class="fk-sql-note">{count}</div>'
        f"</div>"
    )


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


@st.cache_resource
def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _process(question: str, history: list[dict]) -> str:
    """Convert natural language → SQL → run → return HTML-safe response string.

    history: prior messages (role 'user'/'assistant') NOT including current question.
    """
    client = _get_client()
    if client is None:
        return '<em style="color:#F87171">GEMINI_API_KEY not set — chatbot unavailable.</em>'

    # Build multi-turn contents so Gemini has conversation context
    contents: list[types.Content] = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        text = msg["content"] if msg["role"] == "user" else _strip_html(msg["content"])
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            max_output_tokens=512,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw = resp.text
    sql = _extract_sql(raw)
    plain = re.sub(r"```sql.*?```", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()
    display = _render_text(plain)

    if sql:
        try:
            cols, rows = _run_sql(sql)
            table = _table_html(cols, rows)
        except Exception as exc:
            table = (
                f'<div class="fk-sql-error">'
                f"SQL error: {html.escape(str(exc))}"
                f"</div>"
            )
        return display + table
    return display


# ── CCv2 floating component ───────────────────────────────────────────────────
_JS = r"""
export default function({ data, setStateValue, setTriggerValue, parentElement }) {
  const ROOT = 'fk-chat-root';
  const CSS  = 'fk-chat-css';

  /* Persistent <style> in <head> — survives Streamlit reruns */
  if (!document.getElementById(CSS)) {
    const s = document.createElement('style');
    s.id = CSS;
    s.textContent = `
      #fk-chat-btn {
        position:fixed;bottom:24px;right:24px;z-index:9999;
        width:52px;height:52px;border-radius:50%;border:none;cursor:pointer;
        background:linear-gradient(135deg,#F2CC72,#E8B84B);
        box-shadow:0 4px 20px rgba(232,184,75,.45),0 0 0 1px rgba(0,0,0,.25);
        display:flex;align-items:center;justify-content:center;
        transition:transform .18s ease,box-shadow .18s ease;
        color:#0A0A0F;
      }
      #fk-chat-btn:hover{transform:translateY(-2px) scale(1.05);box-shadow:0 8px 28px rgba(232,184,75,.55),0 0 0 1px rgba(0,0,0,.3);}
      #fk-chat-btn svg{width:22px;height:22px;}

      #fk-chat-panel{
        position:fixed;bottom:88px;right:24px;z-index:9998;
        width:390px;height:530px;
        background:#14141B;border:1px solid rgba(255,255,255,.10);
        border-radius:20px;
        box-shadow:0 24px 64px rgba(0,0,0,.75),0 0 0 1px rgba(232,184,75,.07);
        display:flex;flex-direction:column;overflow:hidden;
        transform-origin:bottom right;
        transition:opacity .22s ease,transform .22s cubic-bezier(.34,1.56,.64,1);
      }
      #fk-chat-panel.closed{opacity:0;transform:scale(.88) translateY(14px);pointer-events:none;}
      #fk-chat-panel.open{opacity:1;transform:scale(1) translateY(0);}

      #fk-chat-header{
        display:flex;align-items:center;justify-content:space-between;
        padding:14px 16px 13px;
        background:#1B1B23;
        border-bottom:1px solid rgba(255,255,255,.07);
        flex-shrink:0;
      }
      .fk-ch-brand{display:flex;align-items:center;gap:10px;}
      .fk-ch-mark{
        width:30px;height:30px;border-radius:8px;
        background:linear-gradient(135deg,#F2CC72,#E8B84B);
        display:flex;align-items:center;justify-content:center;
        font-family:'Instrument Serif',serif;font-size:19px;
        color:#0A0A0F;line-height:1;
        box-shadow:0 2px 8px rgba(232,184,75,.3);
      }
      .fk-ch-title{font-size:14px;font-weight:600;color:#ECECEF;letter-spacing:-.1px;}
      .fk-ch-sub{font-size:11px;color:#6B6B78;margin-top:1px;}

      #fk-chat-close{
        background:none;border:none;cursor:pointer;color:#6B6B78;
        padding:5px;border-radius:7px;transition:color .15s,background .15s;
        display:flex;align-items:center;
      }
      #fk-chat-close:hover{color:#ECECEF;background:rgba(255,255,255,.08);}
      #fk-chat-close svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;}

      #fk-chat-messages{
        flex:1;overflow-y:auto;padding:14px 13px 8px;
        display:flex;flex-direction:column;gap:11px;
        scroll-behavior:smooth;
      }
      #fk-chat-messages::-webkit-scrollbar{width:4px;}
      #fk-chat-messages::-webkit-scrollbar-thumb{background:#26262f;border-radius:4px;}

      .fk-msg{display:flex;flex-direction:column;}
      .fk-msg.user{align-items:flex-end;}
      .fk-msg.assistant{align-items:flex-start;}

      .fk-bubble{
        max-width:90%;padding:9px 13px;border-radius:14px;
        font-size:13.5px;line-height:1.6;font-family:'Inter',sans-serif;
      }
      .fk-msg.user .fk-bubble{
        background:linear-gradient(135deg,#E8B84B,#D4A035);
        color:#0A0A0F;font-weight:500;border-bottom-right-radius:4px;
      }
      .fk-msg.assistant .fk-bubble{
        background:#1B1B23;color:#ECECEF;
        border:1px solid rgba(255,255,255,.08);
        border-bottom-left-radius:4px;
      }

      .fk-typing{display:flex;gap:5px;align-items:center;padding:2px 0;}
      .fk-typing span{
        width:7px;height:7px;border-radius:50%;
        background:#E8B84B;opacity:.5;
        animation:fk-bounce 1.2s ease-in-out infinite;
      }
      .fk-typing span:nth-child(2){animation-delay:.2s;}
      .fk-typing span:nth-child(3){animation-delay:.4s;}
      @keyframes fk-bounce{
        0%,60%,100%{transform:translateY(0);opacity:.35;}
        30%{transform:translateY(-5px);opacity:1;}
      }

      .fk-sql-result{
        margin-top:9px;overflow-x:auto;
        border-radius:10px;border:1px solid rgba(255,255,255,.09);
        background:#0A0A0F;
      }
      .fk-sql-result table{width:100%;border-collapse:collapse;font-size:12px;}
      .fk-sql-result th{
        padding:7px 10px;text-align:left;
        color:#9A9AAA;font-size:10.5px;font-weight:600;
        text-transform:uppercase;letter-spacing:.8px;
        border-bottom:1px solid rgba(255,255,255,.07);white-space:nowrap;
      }
      .fk-sql-result td{
        padding:6px 10px;color:#ECECEF;
        border-bottom:1px solid rgba(255,255,255,.04);white-space:nowrap;
      }
      .fk-sql-result tr:last-child td{border-bottom:none;}
      .fk-sql-note{padding:5px 10px;font-size:11px;color:#6B6B78;border-top:1px solid rgba(255,255,255,.05);}
      .fk-sql-error{
        margin-top:9px;padding:8px 12px;border-radius:8px;
        background:rgba(248,113,113,.07);border:1px solid rgba(248,113,113,.2);
        color:#F87171;font-size:12px;
      }

      #fk-chat-footer{
        padding:10px 12px 14px;flex-shrink:0;
        border-top:1px solid rgba(255,255,255,.07);
        background:#14141B;
      }
      #fk-chat-form{display:flex;gap:8px;align-items:center;}
      #fk-chat-input{
        flex:1;background:#1B1B23;border:1px solid rgba(255,255,255,.10);
        border-radius:10px;padding:9px 12px;
        color:#ECECEF;font-size:13.5px;font-family:'Inter',sans-serif;
        outline:none;transition:border-color .15s;
      }
      #fk-chat-input::placeholder{color:#6B6B78;}
      #fk-chat-input:focus{border-color:rgba(232,184,75,.45);}

      #fk-chat-send{
        width:36px;height:36px;border-radius:10px;border:none;cursor:pointer;
        background:linear-gradient(135deg,#F2CC72,#E8B84B);
        color:#0A0A0F;display:flex;align-items:center;justify-content:center;
        transition:transform .15s,opacity .15s;flex-shrink:0;
      }
      #fk-chat-send:hover{transform:scale(1.06);}
      #fk-chat-send:disabled{opacity:.45;cursor:not-allowed;transform:none;}
      #fk-chat-send svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;}

      #fk-chat-empty{
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        height:100%;gap:10px;text-align:center;padding:20px;
        font-family:'Inter',sans-serif;
      }
      .fk-empty-icon{
        width:46px;height:46px;border-radius:13px;
        background:rgba(232,184,75,.1);border:1px solid rgba(232,184,75,.2);
        display:flex;align-items:center;justify-content:center;font-size:22px;
      }
      .fk-empty-title{font-size:14px;font-weight:600;color:#ECECEF;margin:0;}
      .fk-empty-sub{font-size:12.5px;color:#6B6B78;max-width:230px;margin:2px 0 0;line-height:1.5;}
      .fk-suggestions{display:flex;flex-direction:column;gap:6px;margin-top:8px;width:100%;}
      .fk-sug{
        padding:8px 12px;background:#1B1B23;
        border:1px solid rgba(255,255,255,.07);border-radius:9px;
        font-size:12.5px;color:#9A9AAA;cursor:pointer;text-align:left;
        transition:border-color .15s,color .15s;font-family:'Inter',sans-serif;
      }
      .fk-sug:hover{border-color:rgba(232,184,75,.3);color:#E8B84B;}
    `;
    document.head.appendChild(s);
  }

  /* Build DOM once on body — survives reruns */
  let root = document.getElementById(ROOT);
  if (!root) {
    root = document.createElement('div');
    root.id = ROOT;
    document.body.appendChild(root);
    root.innerHTML = `
      <button id="fk-chat-btn" title="Ask Flicker">
        <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
          <circle cx="8" cy="11" r="1" fill="#0A0A0F"/>
          <circle cx="12" cy="11" r="1" fill="#0A0A0F"/>
          <circle cx="16" cy="11" r="1" fill="#0A0A0F"/>
        </svg>
      </button>

      <div id="fk-chat-panel" class="closed">
        <div id="fk-chat-header">
          <div class="fk-ch-brand">
            <div class="fk-ch-mark">F</div>
            <div>
              <div class="fk-ch-title">Ask Flicker</div>
              <div class="fk-ch-sub">Text-to-SQL · Live data</div>
            </div>
          </div>
          <button id="fk-chat-close" title="Close">
            <svg viewBox="0 0 24 24">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div id="fk-chat-messages"></div>

        <div id="fk-chat-footer">
          <div id="fk-chat-form">
            <input id="fk-chat-input" type="text"
              placeholder="Which films are leaving soon?" autocomplete="off"/>
            <button id="fk-chat-send" title="Send">
              <svg viewBox="0 0 24 24">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;

    const btn   = document.getElementById('fk-chat-btn');
    const panel = document.getElementById('fk-chat-panel');
    const close = document.getElementById('fk-chat-close');
    const inp   = document.getElementById('fk-chat-input');
    const send  = document.getElementById('fk-chat-send');

    btn.onclick   = () => { panel.classList.toggle('open'); panel.classList.toggle('closed'); inp.focus(); };
    close.onclick = () => { panel.classList.remove('open'); panel.classList.add('closed'); };

    const doSend = () => {
      const text = inp.value.trim();
      if (!text) return;
      inp.value = '';
      send.disabled = true;

      /* Optimistic: show user bubble + typing immediately */
      const msgsEl = document.getElementById('fk-chat-messages');
      const userDiv = document.createElement('div');
      userDiv.className = 'fk-msg user';
      userDiv.innerHTML = `<div class="fk-bubble">${escHtml(text)}</div>`;
      msgsEl.appendChild(userDiv);

      const typDiv = document.createElement('div');
      typDiv.id = 'fk-typing-tmp';
      typDiv.className = 'fk-msg assistant';
      typDiv.innerHTML = `<div class="fk-bubble"><div class="fk-typing"><span></span><span></span><span></span></div></div>`;
      msgsEl.appendChild(typDiv);
      msgsEl.scrollTop = msgsEl.scrollHeight;

      setTriggerValue('user_message', text);
    };

    send.onclick = doSend;
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') doSend(); });
  }

  /* Update messages on every render */
  const msgs   = Array.isArray(data.messages) ? data.messages : [];
  const msgsEl = document.getElementById('fk-chat-messages');
  const sendEl = document.getElementById('fk-chat-send');

  if (msgs.length === 0) {
    msgsEl.innerHTML = `
      <div id="fk-chat-empty">
        <div class="fk-empty-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="#E8B84B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <p class="fk-empty-title">Ask anything about films</p>
        <p class="fk-empty-sub">What's playing, ratings, box-office, audience vs critics — all from live data.</p>
        <div class="fk-suggestions">
          <button class="fk-sug">Which films are leaving theaters soon?</button>
          <button class="fk-sug">Top 5 genres by average ROI</button>
          <button class="fk-sug">Where do audiences and critics disagree most?</button>
          <button class="fk-sug">Best-rated Horror films currently playing</button>
        </div>
      </div>
    `;
    document.querySelectorAll('.fk-sug').forEach(b => {
      b.onclick = () => {
        if (sendEl) sendEl.disabled = true;
        const msgsEl2 = document.getElementById('fk-chat-messages');
        const userDiv = document.createElement('div');
        userDiv.className = 'fk-msg user';
        userDiv.innerHTML = `<div class="fk-bubble">${escHtml(b.textContent.trim())}</div>`;
        const typDiv = document.createElement('div');
        typDiv.id = 'fk-typing-tmp';
        typDiv.className = 'fk-msg assistant';
        typDiv.innerHTML = `<div class="fk-bubble"><div class="fk-typing"><span></span><span></span><span></span></div></div>`;
        msgsEl2.innerHTML = '';
        msgsEl2.appendChild(userDiv);
        msgsEl2.appendChild(typDiv);
        setTriggerValue('user_message', b.textContent.trim());
      };
    });
  } else {
    msgsEl.innerHTML = msgs.map(m =>
      `<div class="fk-msg ${m.role}">
        <div class="fk-bubble">${m.role === 'user' ? escHtml(m.content) : m.content}</div>
      </div>`
    ).join('');
    msgsEl.scrollTop = msgsEl.scrollHeight;
    if (sendEl) sendEl.disabled = false;
  }
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
"""

_chat_component = stv2.component("flicker_chat", js=_JS, isolate_styles=False)


def render_chat() -> None:
    """Mount the floating chatbot on every page. Call once from app.py."""
    if "fk_msgs" not in st.session_state:
        st.session_state.fk_msgs = []

    result = _chat_component(
        data={"messages": st.session_state.fk_msgs},
        key="flicker_chat",
    )

    if result and result.get("user_message"):
        question = result["user_message"]
        history = list(st.session_state.fk_msgs)  # snapshot before appending
        st.session_state.fk_msgs.append({"role": "user", "content": question})
        answer = _process(question, history)
        st.session_state.fk_msgs.append({"role": "assistant", "content": answer})
        st.rerun()
