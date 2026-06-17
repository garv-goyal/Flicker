"use client";

import { useRef, useState, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tableHtml?: string;
}

const SUGGESTIONS = [
  "Which films are leaving theaters soon?",
  "Top 5 genres by average ROI",
  "Where do audiences and critics disagree most?",
  "Best hidden gems right now",
];

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    const newMsg: Message = { role: "user", content: question };
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, newMsg]);
    setInput("");
    setLoading(true);

    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history, question }),
      });
      const data = await r.json();
      if (!r.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.error ?? "Something went wrong." },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.plain, tableHtml: data.tableHtml },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Network error — please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function renderText(text: string) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        title="Ask Flicker"
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 300,
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          border: "none",
          cursor: "pointer",
          background: "linear-gradient(145deg, var(--accent), #00a3c4)",
          boxShadow: open
            ? "0 4px 20px rgba(0,212,255,0.3), 0 0 0 1px rgba(0,0,0,0.25)"
            : "0 4px 20px rgba(0,212,255,0.4), 0 0 0 1px rgba(0,0,0,0.25), 0 0 0 5px rgba(0,212,255,0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#060810",
          transition: "transform 0.18s ease, box-shadow 0.18s ease",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px) scale(1.05)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.transform = "";
        }}
      >
        {open ? (
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 3c-4.97 0-9 3.5-9 7.8 0 2.45 1.27 4.63 3.28 6.08-.1.97-.46 2.2-1.4 3.4a.5.5 0 00.5.8c2.1-.5 3.6-1.45 4.5-2.2.68.13 1.39.2 2.12.2 4.97 0 9-3.5 9-7.8s-4.03-7.8-9-7.8z" fill="#060810" />
            <circle cx="8.3" cy="10.6" r="1.15" fill="var(--accent)" />
            <circle cx="12" cy="10.6" r="1.15" fill="var(--accent)" />
            <circle cx="15.7" cy="10.6" r="1.15" fill="var(--accent)" />
          </svg>
        )}
      </button>

      {/* Panel */}
      <div
        style={{
          position: "fixed",
          bottom: "92px",
          right: "24px",
          zIndex: 299,
          width: "400px",
          height: "560px",
          background: "var(--surface)",
          border: "1px solid var(--border-2)",
          borderRadius: "22px",
          boxShadow: "0 24px 64px rgba(0,0,0,0.75), 0 0 0 1px rgba(0,212,255,0.06)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          transformOrigin: "bottom right",
          transition: "opacity 0.22s ease, transform 0.22s cubic-bezier(0.34,1.56,0.64,1)",
          opacity: open ? 1 : 0,
          transform: open ? "scale(1) translateY(0)" : "scale(0.88) translateY(14px)",
          pointerEvents: open ? "all" : "none",
        }}
      >
        {/* Header */}
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 16px 14px",
            background: "linear-gradient(135deg, var(--surface-2), var(--surface-3))",
            borderBottom: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "2px",
              background: "linear-gradient(90deg, transparent, var(--accent), transparent)",
              opacity: 0.6,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "10px",
                background: "linear-gradient(145deg, var(--accent), #00a3c4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 2px 10px rgba(0,212,255,0.3)",
              }}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M12 3c-4.97 0-9 3.5-9 7.8 0 2.45 1.27 4.63 3.28 6.08-.1.97-.46 2.2-1.4 3.4a.5.5 0 00.5.8c2.1-.5 3.6-1.45 4.5-2.2.68.13 1.39.2 2.12.2 4.97 0 9-3.5 9-7.8s-4.03-7.8-9-7.8z" fill="#060810" />
                <circle cx="8.3" cy="10.6" r="1.05" fill="var(--accent)" />
                <circle cx="12" cy="10.6" r="1.05" fill="var(--accent)" />
                <circle cx="15.7" cy="10.6" r="1.05" fill="var(--accent)" />
              </svg>
            </div>
            <div>
              <div style={{ fontSize: "14.5px", fontWeight: 600, color: "var(--text)" }}>Ask Flicker</div>
              <div style={{ fontSize: "11px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "5px" }}>
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--success)", display: "inline-block" }} />
                Live film data
              </div>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--muted)",
              padding: "6px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              transition: "background 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--border)";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "none";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--muted)";
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "14px 13px 8px",
            display: "flex",
            flexDirection: "column",
            gap: "11px",
            scrollBehavior: "smooth",
          }}
        >
          {messages.length === 0 && !loading ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                gap: "10px",
                textAlign: "center",
                padding: "20px",
              }}
            >
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "16px",
                  background: "linear-gradient(145deg, var(--accent-dim2), var(--accent-dim))",
                  border: "1px solid rgba(0,212,255,0.22)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 8px 24px rgba(0,212,255,0.12)",
                }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M12 3c-4.97 0-9 3.5-9 7.8 0 2.45 1.27 4.63 3.28 6.08-.1.97-.46 2.2-1.4 3.4a.5.5 0 00.5.8c2.1-.5 3.6-1.45 4.5-2.2.68.13 1.39.2 2.12.2 4.97 0 9-3.5 9-7.8s-4.03-7.8-9-7.8z" fill="var(--accent-dim2)" stroke="var(--accent)" strokeWidth="1.3" />
                  <circle cx="8.3" cy="10.6" r="1.15" fill="var(--accent)" />
                  <circle cx="12" cy="10.6" r="1.15" fill="var(--accent)" />
                  <circle cx="15.7" cy="10.6" r="1.15" fill="var(--accent)" />
                </svg>
              </div>
              <p style={{ fontSize: "14.5px", fontWeight: 600, color: "var(--text)", margin: 0 }}>
                Ask anything about films
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", maxWidth: "240px", margin: "2px 0 0", lineHeight: 1.5 }}>
                Ratings, box office, audience vs critics — straight from our film data.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "7px", marginTop: "10px", width: "100%" }}>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "9px 13px",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                      borderRadius: "10px",
                      fontSize: "12.5px",
                      color: "var(--muted)",
                      cursor: "pointer",
                      textAlign: "left",
                      fontFamily: "var(--font-ui)",
                      transition: "border-color 0.15s, color 0.15s, transform 0.15s, background 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      const el = e.currentTarget as HTMLButtonElement;
                      el.style.borderColor = "rgba(0,212,255,0.32)";
                      el.style.color = "var(--accent)";
                      el.style.background = "var(--surface-3)";
                      el.style.transform = "translateX(2px)";
                    }}
                    onMouseLeave={(e) => {
                      const el = e.currentTarget as HTMLButtonElement;
                      el.style.borderColor = "var(--border)";
                      el.style.color = "var(--muted)";
                      el.style.background = "var(--surface-2)";
                      el.style.transform = "";
                    }}
                  >
                    <span style={{ color: "var(--accent)", opacity: 0.7, flexShrink: 0 }}>›</span>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((m, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: m.role === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "90%",
                      padding: "9px 13px",
                      borderRadius: m.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                      fontSize: "13.5px",
                      lineHeight: 1.6,
                      background: m.role === "user" ? "var(--accent)" : "var(--surface-2)",
                      color: m.role === "user" ? "#060810" : "var(--text)",
                      border: m.role === "assistant" ? "1px solid var(--border)" : "none",
                      fontWeight: m.role === "user" ? 500 : 400,
                    }}
                    dangerouslySetInnerHTML={{
                      __html: m.role === "user"
                        ? m.content.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                        : renderText(m.content),
                    }}
                  />
                  {m.tableHtml && (
                    <div
                      style={{
                        marginTop: "8px",
                        maxWidth: "100%",
                        overflowX: "auto",
                        borderRadius: "10px",
                        border: "1px solid var(--border)",
                        background: "var(--bg)",
                        fontSize: "12px",
                      }}
                      dangerouslySetInnerHTML={{ __html: m.tableHtml }}
                    />
                  )}
                </div>
              ))}
              {loading && (
                <div style={{ display: "flex", alignItems: "flex-start" }}>
                  <div
                    style={{
                      padding: "9px 13px",
                      borderRadius: "14px 14px 14px 4px",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                      display: "flex",
                      gap: "5px",
                      alignItems: "center",
                    }}
                  >
                    {[0, 0.2, 0.4].map((delay, i) => (
                      <span
                        key={i}
                        style={{
                          width: "7px",
                          height: "7px",
                          borderRadius: "50%",
                          background: "var(--accent)",
                          opacity: 0.5,
                          animation: `chatBounce 1.2s ease-in-out ${delay}s infinite`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Input */}
        <div
          style={{
            padding: "10px 12px 14px",
            flexShrink: 0,
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
          }}
        >
          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            style={{
              display: "flex",
              gap: "6px",
              alignItems: "center",
              background: "var(--surface-2)",
              border: "1px solid var(--border-2)",
              borderRadius: "24px",
              padding: "5px 5px 5px 16px",
              transition: "border-color 0.15s",
            }}
            onFocus={(e) => { (e.currentTarget as HTMLFormElement).style.borderColor = "rgba(0,212,255,0.4)"; }}
            onBlur={(e) => { (e.currentTarget as HTMLFormElement).style.borderColor = "var(--border-2)"; }}
          >
            <input
              ref={inputRef}
              type="text"
              placeholder="Which films are leaving soon?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                padding: "9px 0",
                color: "var(--text)",
                fontFamily: "var(--font-ui)",
                fontSize: "13.5px",
                outline: "none",
                caretColor: "var(--accent)",
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "50%",
                border: "none",
                cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                background: "linear-gradient(145deg, var(--accent), #00a3c4)",
                color: "#060810",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: loading || !input.trim() ? 0.4 : 1,
                transition: "transform 0.15s, opacity 0.15s",
                flexShrink: 0,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      </div>

      <style>{`
        @keyframes chatBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
          30% { transform: translateY(-5px); opacity: 1; }
        }
        .chat-row-count {
          padding: 4px 10px;
          font-size: 11px;
          color: var(--muted);
          border-top: 1px solid rgba(255,255,255,0.05);
        }
        .chat-error-note {
          padding: 8px 10px;
          font-size: 12px;
          color: var(--danger);
        }
        [style*="background: var(--bg)"] table {
          width: 100%;
          border-collapse: collapse;
        }
        [style*="background: var(--bg)"] th {
          padding: 6px 10px;
          text-align: left;
          color: var(--muted);
          font-size: 10.5px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          border-bottom: 1px solid var(--border);
          white-space: nowrap;
        }
        [style*="background: var(--bg)"] td {
          padding: 5px 10px;
          color: var(--text);
          font-size: 12px;
          border-bottom: 1px solid rgba(255,255,255,0.04);
          white-space: nowrap;
          font-family: var(--font-mono);
        }
        [style*="background: var(--bg)"] tr:last-child td {
          border-bottom: none;
        }
      `}</style>
    </>
  );
}
