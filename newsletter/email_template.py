"""Build the weekly newsletter HTML email.

Color palette mirrors the web app:
  bg         #0A0A0F
  surface    #14141B
  surface-2  #1B1B23
  border     rgba(255,255,255,0.07)
  gold       #E8B84B
  text       #ECECEF
  muted      #9A9AAA
  green      #34D399
  red        #F87171
"""
from datetime import date


# ── helpers ──────────────────────────────────────────────────────────────────

def _rating_bar(value: float, max_val: float = 10.0, color: str = "#E8B84B") -> str:
    pct = min(100, round(value / max_val * 100))
    return f"""
    <div style="background:#1B1B23;border-radius:4px;height:6px;width:100%;margin-top:4px;">
      <div style="background:{color};width:{pct}%;height:6px;border-radius:4px;"></div>
    </div>"""


def _sentiment_bar(pct: float | None, color: str = "#34D399") -> str:
    if pct is None:
        return '<span style="color:#6B6B78;font-size:12px;">No sentiment data</span>'
    p = min(100, round(pct))
    return f"""
    <div style="background:#1B1B23;border-radius:4px;height:6px;width:100%;margin-top:4px;">
      <div style="background:{color};width:{p}%;height:6px;border-radius:4px;"></div>
    </div>"""


def _genre_pill(genre: str | None) -> str:
    if not genre:
        return ""
    return (
        f'<span style="background:rgba(232,184,75,0.14);color:#E8B84B;'
        f'border:1px solid rgba(232,184,75,0.3);border-radius:999px;'
        f'padding:3px 12px;font-size:12px;font-weight:600;">{genre}</span>'
    )


def _status_pill(status: str) -> str:
    styles = {
        "Now Playing": ("rgba(52,211,153,0.08)", "#34D399", "rgba(52,211,153,0.3)"),
        "Holdover":    ("rgba(232,184,75,0.08)", "#E8B84B", "rgba(232,184,75,0.3)"),
        "Leaving Soon": ("rgba(248,113,113,0.08)", "#F87171", "rgba(248,113,113,0.3)"),
    }
    bg, fg, border = styles.get(status, ("rgba(155,155,170,0.08)", "#9A9AAA", "rgba(155,155,170,0.3)"))
    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'border-radius:999px;padding:3px 12px;font-size:12px;font-weight:600;">{status}</span>'
    )


# ── main builder ─────────────────────────────────────────────────────────────

def build_email(picks: dict, subscriber_email: str, genre_pref: str | None = None) -> str:
    today = date.today().strftime("%B %d, %Y")
    main = picks.get("main_pick")
    leaving = picks.get("leaving_soon")
    underrated = picks.get("underrated")
    overrated = picks.get("overrated")
    runners = picks.get("runners", [])

    # ── subject helper (returned separately) ─────────────────────────────────
    # subject is built in send_newsletter.py from picks["main_pick"]["title"]

    # ── main pick section ─────────────────────────────────────────────────────
    if main:
        main_title = main.get("title", "—")
        main_genre = main.get("primary_genre")
        main_status = main.get("status", "")
        main_rating = float(main.get("vote_average", 0))
        main_popularity = float(main.get("popularity", 0))
        main_votes = int(main.get("vote_count", 0))
        main_sentiment = main.get("pct_positive")  # may be None
        main_critic = main.get("critic_score")     # may be None

        why_parts = []
        if main_rating > 0:
            why_parts.append(f"TMDB {main_rating:.1f}/10")
        if main_critic is not None:
            why_parts.append(f"Critics {int(main_critic)}%")
        if main_sentiment is not None:
            why_parts.append(f"Audience {int(main_sentiment)}% positive")
        if main_popularity > 0:
            why_parts.append(f"Popularity {main_popularity:.0f}")
        why_line = " &nbsp;·&nbsp; ".join(why_parts) if why_parts else "Trending now"

        pick_section = f"""
        <!-- MAIN PICK -->
        <tr><td style="padding:0 32px 24px;">

          <div style="background:linear-gradient(135deg,#1B1B23,#14141B);
                      border:1px solid rgba(232,184,75,0.2);
                      border-radius:12px;overflow:hidden;">

            <!-- gold top bar -->
            <div style="height:3px;background:linear-gradient(90deg,#F2CC72,#E8B84B,rgba(232,184,75,0));"></div>

            <div style="padding:28px 28px 24px;">
              <!-- eyebrow -->
              <div style="font-size:11px;letter-spacing:2.5px;text-transform:uppercase;
                          color:#E8B84B;font-weight:600;margin-bottom:12px;">
                {"· " + genre_pref + " pick" if genre_pref else "·  this week's pick"}
              </div>

              <!-- title -->
              <div style="font-size:28px;font-weight:700;color:#ECECEF;
                          line-height:1.2;margin-bottom:12px;">{main_title}</div>

              <!-- pills row -->
              <div style="margin-bottom:20px;">
                {_status_pill(main_status)}
                &nbsp;&nbsp;
                {_genre_pill(main_genre) if main_genre else ""}
              </div>

              <!-- metrics grid -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td width="33%" style="padding-right:12px;">
                    <div style="color:#9A9AAA;font-size:11px;text-transform:uppercase;
                                letter-spacing:1.5px;margin-bottom:2px;">TMDB Rating</div>
                    <div style="color:#ECECEF;font-size:22px;font-weight:700;">{main_rating:.1f}
                      <span style="color:#9A9AAA;font-size:13px;font-weight:400;">/10</span>
                    </div>
                    {_rating_bar(main_rating, 10.0, "#E8B84B")}
                  </td>
                  <td width="33%" style="padding-right:12px;">
                    <div style="color:#9A9AAA;font-size:11px;text-transform:uppercase;
                                letter-spacing:1.5px;margin-bottom:2px;">Popularity</div>
                    <div style="color:#ECECEF;font-size:22px;font-weight:700;">{main_popularity:.0f}</div>
                    {_rating_bar(min(main_popularity, 300), 300.0, "#34D399")}
                  </td>
                  <td width="33%">
                    <div style="color:#9A9AAA;font-size:11px;text-transform:uppercase;
                                letter-spacing:1.5px;margin-bottom:2px;">Audience Buzz</div>
                    <div style="color:#ECECEF;font-size:22px;font-weight:700;">
                      {f"{int(main_sentiment)}%" if main_sentiment is not None else "—"}
                    </div>
                    {_sentiment_bar(main_sentiment)}
                  </td>
                </tr>
              </table>

              <!-- why line -->
              <div style="background:#0A0A0F;border-radius:8px;padding:12px 16px;
                          font-size:13px;color:#9A9AAA;border:1px solid rgba(255,255,255,0.06);">
                <span style="color:#E8B84B;">&#9654;</span> &nbsp;{why_line}
              </div>
            </div>
          </div>

        </td></tr>
        """
    else:
        pick_section = ""

    # ── runners-up ────────────────────────────────────────────────────────────
    if runners:
        runner_rows = ""
        for i, r in enumerate(runners):
            border_b = "border-bottom:1px solid rgba(255,255,255,0.06);" if i < len(runners) - 1 else ""
            r_sentiment = f"  ·  {int(r['pct_positive'])}% positive" if r.get("pct_positive") is not None else ""
            runner_rows += f"""
            <tr>
              <td style="padding:12px 0;{border_b}">
                <span style="color:#ECECEF;font-size:14px;font-weight:600;">{r['title']}</span>
                <span style="color:#6B6B78;font-size:13px;margin-left:8px;">
                  {_genre_pill(r.get('primary_genre')) if r.get('primary_genre') else ""}
                </span>
              </td>
              <td style="text-align:right;padding:12px 0;{border_b}color:#9A9AAA;font-size:13px;">
                <span style="color:#E8B84B;font-weight:600;">{float(r['vote_average']):.1f}</span>/10
                {r_sentiment}
              </td>
            </tr>"""

        runners_section = f"""
        <!-- RUNNERS UP -->
        <tr><td style="padding:0 32px 24px;">
          <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;
                      color:#6B6B78;margin-bottom:12px;">Also worth watching</div>
          <div style="background:#14141B;border:1px solid rgba(255,255,255,0.07);
                      border-radius:10px;padding:0 20px;">
            <table width="100%" cellpadding="0" cellspacing="0">{runner_rows}</table>
          </div>
        </td></tr>
        """
    else:
        runners_section = ""

    # ── leaving soon ─────────────────────────────────────────────────────────
    if leaving:
        ls_title = leaving.get("title", "—")
        ls_rating = float(leaving.get("vote_average", 0))
        ls_genre = leaving.get("primary_genre")
        ls_section = f"""
        <!-- LEAVING SOON -->
        <tr><td style="padding:0 32px 24px;">
          <div style="background:#14141B;border:1px solid rgba(248,113,113,0.2);
                      border-radius:10px;padding:20px 24px;">
            <div style="display:flex;align-items:center;margin-bottom:6px;">
              <span style="font-size:11px;letter-spacing:2px;text-transform:uppercase;
                            color:#F87171;font-weight:600;">Leaving Soon — last chance</span>
            </div>
            <div style="font-size:18px;font-weight:700;color:#ECECEF;margin-bottom:8px;">
              {ls_title}
            </div>
            <div>
              {_genre_pill(ls_genre) if ls_genre else ""}
              &nbsp;
              <span style="color:#9A9AAA;font-size:13px;">
                Rated <span style="color:#E8B84B;font-weight:600;">{ls_rating:.1f}/10</span>
                &nbsp;·&nbsp; Only a few more days in theaters.
              </span>
            </div>
          </div>
        </td></tr>
        """
    else:
        ls_section = ""

    # ── critics vs crowds ─────────────────────────────────────────────────────
    if underrated or overrated:
        def _divergence_card(film: dict, direction: str) -> str:
            if not film:
                return '<td width="50%"></td>'
            title = film.get("title", "—")
            pct = film.get("pct_positive")
            critic = film.get("critic_score")
            div = abs(float(film.get("divergence", 0)))
            if direction == "crowd":
                label = "Crowd favourite"
                label_color = "#34D399"
                sub = f"Audience {int(pct)}% · Critics {int(critic)}% &nbsp;({'+' if div else ''}{div:.0f} pts)"
            else:
                label = "Critical darling"
                label_color = "#F87171"
                sub = f"Critics {int(critic)}% · Audience {int(pct)}% &nbsp;(−{div:.0f} pts)"
            return f"""
            <td width="50%" style="padding-right:{6 if direction == 'crowd' else 0}px;">
              <div style="background:#14141B;border:1px solid rgba(255,255,255,0.07);
                          border-radius:10px;padding:16px 18px;height:100%;">
                <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;
                            color:{label_color};font-weight:600;margin-bottom:8px;">{label}</div>
                <div style="font-size:15px;font-weight:700;color:#ECECEF;margin-bottom:8px;">{title}</div>
                <div style="font-size:12px;color:#9A9AAA;">{sub}</div>
              </div>
            </td>"""

        cvc_section = f"""
        <!-- CRITICS VS CROWDS -->
        <tr><td style="padding:0 32px 24px;">
          <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;
                      color:#6B6B78;margin-bottom:12px;">Critics vs Crowds this week</div>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              {_divergence_card(underrated, "crowd")}
              <td width="12px"></td>
              {_divergence_card(overrated, "critics")}
            </tr>
          </table>
        </td></tr>
        """
    else:
        cvc_section = ""

    # ── assemble full email ───────────────────────────────────────────────────
    unsubscribe_note = (
        f'<a href="mailto:newsletter@flickerdata.io?subject=Unsubscribe&body={subscriber_email}" '
        f'style="color:#6B6B78;text-decoration:underline;">Unsubscribe</a>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="dark">
  <title>Flicker Weekly</title>
</head>
<body style="margin:0;padding:0;background:#0A0A0F;font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif;">

  <!-- outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0F;min-height:100vh;">
  <tr><td align="center" style="padding:32px 16px;">

    <!-- card -->
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#0E0E14;
                  border:1px solid rgba(255,255,255,0.07);border-radius:16px;
                  overflow:hidden;">

      <!-- ── HEADER ─────────────────────────────────────────────────────── -->
      <tr>
        <td style="background:linear-gradient(180deg,#14141B,#0E0E14);
                   padding:28px 32px 20px;
                   border-bottom:1px solid rgba(255,255,255,0.07);">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <!-- logo mark + wordmark -->
                <table cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="width:36px;height:36px;border-radius:9px;
                                background:linear-gradient(135deg,#F2CC72,#E8B84B);
                                text-align:center;vertical-align:middle;">
                      <span style="font-size:22px;color:#0A0A0F;font-weight:700;
                                   line-height:36px;display:block;">F</span>
                    </td>
                    <td style="padding-left:12px;vertical-align:middle;">
                      <div style="font-size:20px;font-weight:700;color:#E8B84B;
                                  letter-spacing:0.5px;line-height:1;">Flicker</div>
                      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;
                                  color:#6B6B78;margin-top:1px;">Film Intelligence</div>
                    </td>
                  </tr>
                </table>
              </td>
              <td align="right" style="vertical-align:middle;">
                <div style="font-size:12px;color:#6B6B78;">{today}</div>
                <div style="font-size:11px;color:#E8B84B;letter-spacing:1.5px;
                            text-transform:uppercase;margin-top:2px;">Weekly Edition</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- ── INTRO ──────────────────────────────────────────────────────── -->
      <tr>
        <td style="padding:24px 32px 16px;">
          <div style="font-size:14px;color:#9A9AAA;line-height:1.6;">
            Your weekly data-backed guide to what's worth watching.
            {f'Picks filtered for <strong style="color:#E8B84B;">{genre_pref}</strong>.' if genre_pref else ""}
          </div>
          <div style="height:1px;background:rgba(255,255,255,0.06);margin-top:20px;"></div>
        </td>
      </tr>

      {pick_section}
      {runners_section}
      {ls_section}
      {cvc_section}

      <!-- ── FOOTER ─────────────────────────────────────────────────────── -->
      <tr>
        <td style="padding:20px 32px 28px;border-top:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:12px;color:#6B6B78;line-height:1.7;text-align:center;">
            Data from TMDB, OMDb &amp; YouTube &nbsp;·&nbsp;
            Processed by Kafka → DuckDB → dbt &nbsp;·&nbsp;
            {unsubscribe_note}
          </div>
          <div style="font-size:11px;color:#3D3D4A;text-align:center;margin-top:8px;">
            Flicker &nbsp;·&nbsp; Entertainment analytics
          </div>
        </td>
      </tr>

    </table>
    <!-- /card -->

  </td></tr>
  </table>

</body>
</html>"""

    return html


def subject_line(picks: dict) -> str:
    main = picks.get("main_pick")
    if main:
        return f"Flicker Weekly · Watch {main['title']} this weekend"
    return "Flicker Weekly · Your movie picks this weekend"
