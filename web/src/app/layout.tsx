import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/nav";
import Ticker from "@/components/ticker";
import Chatbot from "@/components/chatbot";

export const metadata: Metadata = {
  title: "Flicker — Film Intelligence",
  description:
    "Box office returns, critic scores, and audience sentiment across thousands of films — surfaced as patterns.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col" style={{ fontFamily: "var(--font-ui)" }}>
        <Nav />
        <Ticker />
        <main style={{ flex: 1 }}>{children}</main>
        <Chatbot />
        <footer
          style={{
            borderTop: "1px solid var(--border)",
            padding: "24px",
            textAlign: "center",
            fontSize: "12px",
            color: "var(--faint)",
            marginTop: "64px",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.04em",
          }}
        >
          FLICKER · Film Intelligence · Data from TMDB, OMDb, Rotten Tomatoes
        </footer>
      </body>
    </html>
  );
}
