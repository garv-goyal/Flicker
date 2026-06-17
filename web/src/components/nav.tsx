"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import VerdictSearch from "./verdict-search";

const LINKS = [
  { href: "/", label: "Pulse" },
  { href: "/critics", label: "Critics" },
  { href: "/hype", label: "Hype" },
  { href: "/discover", label: "Discover" },
  { href: "/newsletter", label: "Newsletter" },
];

export default function Nav() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link href="/" className="nav-logo">
            FLIC<span>K</span>ER
          </Link>

          <div className="nav-links">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`nav-link ${pathname === l.href ? "active" : ""}`}
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="nav-actions">
            <button
              className="nav-btn"
              onClick={() => setSearchOpen(true)}
              title="Search films"
              aria-label="Search films"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {searchOpen && <VerdictSearch onClose={() => setSearchOpen(false)} />}
    </>
  );
}
