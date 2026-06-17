"use client";

import { useState } from "react";

const GENRES = [
  "No preference", "Action", "Comedy", "Drama", "Horror",
  "Science Fiction", "Thriller", "Family", "Animation", "Romance",
];

export default function NewsletterPage() {
  const [email, setEmail] = useState("");
  const [genre, setGenre] = useState("No preference");
  const [status, setStatus] = useState<"idle" | "loading" | "new" | "updated" | "exists" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const [unsubEmail, setUnsubEmail] = useState("");
  const [unsubStatus, setUnsubStatus] = useState<"idle" | "done" | "error">("idle");

  async function handleSubscribe(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");
    try {
      const r = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), genre: genre === "No preference" ? null : genre }),
      });
      const data = await r.json();
      if (!r.ok) { setErrorMsg(data.error ?? "Something went wrong."); setStatus("error"); return; }
      setStatus(data.result); // "new" | "updated" | "exists"
    } catch {
      setErrorMsg("Network error — try again.");
      setStatus("error");
    }
  }

  async function handleUnsubscribe(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await fetch("/api/newsletter/subscribe", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: unsubEmail.trim().toLowerCase() }),
      });
      setUnsubStatus(r.ok ? "done" : "error");
    } catch {
      setUnsubStatus("error");
    }
  }

  return (
    <div className="page-wrap">
      <div className="hero">
        <div className="eyebrow">Flicker · Weekly</div>
        <h1>
          Film intel,<br />
          <em>once a week.</em>
        </h1>
        <p>
          Every Sunday, Flicker queries live theater data — popularity trends,
          audience sentiment, critic divergence — and builds a data-backed
          recommendation. No guesswork, no sponsored picks.
        </p>
      </div>

      <div className="divider" />

      {/* What's in each issue */}
      <div style={{ marginBottom: "40px" }}>
        <div className="section-head">
          <h2>What&rsquo;s inside every issue</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
          {[
            {
              num: "01",
              label: "This week's pick",
              desc: "One film, scored across TMDB rating, audience buzz, and popularity trend. Genre-filtered if you set a preference.",
            },
            {
              num: "02",
              label: "Leaving soon",
              desc: "The best-rated film entering its final week in theaters. Catch it before it's gone.",
            },
            {
              num: "03",
              label: "Critics vs audiences",
              desc: "Where opinion diverges most — films audiences love that critics underrated, and the reverse.",
            },
          ].map((item) => (
            <div className="card" key={item.num}>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "28px",
                  fontWeight: 700,
                  color: "var(--accent)",
                  opacity: 0.4,
                  marginBottom: "12px",
                  lineHeight: 1,
                  letterSpacing: "-0.02em",
                }}
              >
                {item.num}
              </div>
              <div style={{ fontWeight: 600, fontSize: "15px", marginBottom: "6px" }}>
                {item.label}
              </div>
              <div style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.6 }}>
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Subscribe form */}
      <div className="page-grid-2">
        <div>
          <div className="section-head">
            <h2>Subscribe</h2>
            <p>Free, weekly, unsubscribe any time.</p>
          </div>

          <div className="card">
            {status === "new" ? (
              <div style={{ padding: "8px 0" }}>
                <div style={{ color: "var(--success)", fontWeight: 600, marginBottom: "6px" }}>
                  You&rsquo;re in.
                </div>
                <div style={{ color: "var(--muted)", fontSize: "13px" }}>
                  First email lands this Sunday.{" "}
                  {genre !== "No preference" && (
                    <span>
                      Picks filtered for <strong style={{ color: "var(--text)" }}>{genre}</strong>.
                    </span>
                  )}
                </div>
              </div>
            ) : status === "updated" ? (
              <div style={{ padding: "8px 0" }}>
                <div style={{ color: "var(--warn)", fontWeight: 600, marginBottom: "6px" }}>
                  Preferences updated.
                </div>
                <div style={{ color: "var(--muted)", fontSize: "13px" }}>
                  Changes take effect from the next send.
                </div>
              </div>
            ) : status === "exists" ? (
              <div style={{ padding: "8px 0" }}>
                <div style={{ color: "var(--muted)", fontSize: "13px" }}>
                  You&rsquo;re already subscribed with those preferences.
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubscribe} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label
                    htmlFor="email"
                    style={{ display: "block", fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--muted)", marginBottom: "8px" }}
                  >
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border-2)",
                      borderRadius: "8px",
                      padding: "10px 14px",
                      color: "var(--text)",
                      fontFamily: "var(--font-ui)",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label
                    htmlFor="genre"
                    style={{ display: "block", fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--muted)", marginBottom: "8px" }}
                  >
                    Genre preference
                  </label>
                  <select
                    id="genre"
                    value={genre}
                    onChange={(e) => setGenre(e.target.value)}
                    style={{
                      width: "100%",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border-2)",
                      borderRadius: "8px",
                      padding: "10px 14px",
                      color: "var(--text)",
                      fontFamily: "var(--font-ui)",
                      fontSize: "14px",
                      outline: "none",
                      cursor: "pointer",
                    }}
                  >
                    {GENRES.map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>

                {status === "error" && (
                  <div style={{ fontSize: "13px", color: "var(--danger)" }}>{errorMsg}</div>
                )}

                <button
                  type="submit"
                  disabled={status === "loading"}
                  style={{
                    background: "var(--accent)",
                    color: "#060810",
                    border: "none",
                    borderRadius: "8px",
                    padding: "12px 20px",
                    fontFamily: "var(--font-ui)",
                    fontSize: "14px",
                    fontWeight: 600,
                    cursor: status === "loading" ? "wait" : "pointer",
                    opacity: status === "loading" ? 0.7 : 1,
                    transition: "opacity 0.15s",
                  }}
                >
                  {status === "loading" ? "Subscribing…" : "Subscribe →"}
                </button>
              </form>
            )}
          </div>

          {/* Unsubscribe */}
          <details style={{ marginTop: "16px" }}>
            <summary
              style={{
                fontSize: "12px",
                color: "var(--muted)",
                cursor: "pointer",
                padding: "8px 0",
                listStyle: "none",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span>Unsubscribe</span>
            </summary>
            <div className="card" style={{ marginTop: "12px" }}>
              {unsubStatus === "done" ? (
                <div style={{ fontSize: "13px", color: "var(--muted)" }}>Removed.</div>
              ) : (
                <form onSubmit={handleUnsubscribe} style={{ display: "flex", gap: "10px" }}>
                  <input
                    type="email"
                    required
                    placeholder="you@example.com"
                    value={unsubEmail}
                    onChange={(e) => setUnsubEmail(e.target.value)}
                    style={{
                      flex: 1,
                      background: "var(--surface-2)",
                      border: "1px solid var(--border-2)",
                      borderRadius: "8px",
                      padding: "9px 12px",
                      color: "var(--text)",
                      fontFamily: "var(--font-ui)",
                      fontSize: "13px",
                      outline: "none",
                    }}
                  />
                  <button
                    type="submit"
                    style={{
                      background: "var(--surface-3)",
                      border: "1px solid var(--border-2)",
                      borderRadius: "8px",
                      padding: "9px 16px",
                      color: "var(--muted)",
                      fontFamily: "var(--font-ui)",
                      fontSize: "13px",
                      cursor: "pointer",
                    }}
                  >
                    Remove
                  </button>
                </form>
              )}
              {unsubStatus === "error" && (
                <div style={{ fontSize: "12px", color: "var(--danger)", marginTop: "8px" }}>
                  Something went wrong.
                </div>
              )}
            </div>
          </details>
        </div>

        {/* Right: what you get */}
        <div>
          <div className="section-head">
            <h2>What you&rsquo;ll get</h2>
          </div>
          <div className="card" style={{ padding: "28px 24px" }}>
            {[
              {
                label: "Main pick",
                desc: "One film scored on TMDB rating, audience buzz and popularity. Genre-filtered first if you set a preference, then all genres.",
              },
              {
                label: "Leaving soon",
                desc: "The best-rated film entering its final week in theaters. Catch it before it leaves.",
              },
              {
                label: "Critics vs crowds",
                desc: "Where audience sentiment diverges most from critic scores — the underrated gems and the overhyped ones.",
              },
            ].map((item, i, arr) => (
              <div
                key={item.label}
                style={{
                  paddingBottom: i < arr.length - 1 ? "20px" : 0,
                  marginBottom: i < arr.length - 1 ? "20px" : 0,
                  borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "5px" }}>
                  {item.label}
                </div>
                <div style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.6 }}>
                  {item.desc}
                </div>
              </div>
            ))}
          </div>

          <div className="insight" style={{ marginTop: "16px" }}>
            <div className="insight-label">Powered by your data</div>
            <p className="insight-text">
              Every pick is generated from your DuckDB pipeline — TMDB ratings, trailer views,
              box office returns. No editors, no sponsors.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
