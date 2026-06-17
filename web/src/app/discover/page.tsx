import DiscoverClient from "@/components/discover-client";

export default function DiscoverPage() {
  return (
    <div className="page-wrap">
      <div className="hero">
        <div className="eyebrow">Mood · Vibe · Discovery</div>
        <h1>
          What are you<br />
          <em>in the mood for?</em>
        </h1>
        <p>
          Skip the genre dropdown. Pick a vibe — we&rsquo;ll surface the films that
          actually fit, ranked by score and filtered for quality.
        </p>
      </div>
      <div className="divider" style={{ marginTop: "0" }} />
      <DiscoverClient />
    </div>
  );
}
