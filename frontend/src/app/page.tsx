"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getLatestRecalls, searchRecalls, type Recall } from "@/lib/api";

const PRODUCT_FILTERS = [
  { label: "All", value: "" },
  { label: "Toys & Children", value: "children" },
  { label: "Furniture", value: "furniture" },
  { label: "Electronics", value: "electronics" },
  { label: "Appliances", value: "appliances" },
  { label: "Clothing", value: "clothing" },
  { label: "Sports & Recreation", value: "sports" },
];

export default function HomePage() {
  const router = useRouter();
  const [recalls, setRecalls] = useState<Recall[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [isSearchResults, setIsSearchResults] = useState(false);
  const [productFilter, setProductFilter] = useState("");

  const loadLatest = useCallback(async () => {
    setLoading(true);
    setIsSearchResults(false);
    try {
      const data = await getLatestRecalls(24);
      setRecalls(data);
    } catch {
      setRecalls([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadLatest(); }, [loadLatest]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return loadLatest();

    setSearching(true);
    setIsSearchResults(true);
    try {
      const data = await searchRecalls(q, 12);
      setRecalls(data);
    } catch {
      setRecalls([]);
    } finally {
      setSearching(false);
    }
  };

  const goToChat = () => {
    if (query.trim()) {
      router.push(`/chat?q=${encodeURIComponent(query.trim())}`);
    } else {
      router.push("/chat");
    }
  };

  return (
    <>
      {/* Hero */}
      <section className="recalls-hero" aria-labelledby="hero-heading">
        <div className="grid-container">
          <h1 id="hero-heading">Consumer Product Recall Search</h1>
          <p>
            Search recalls issued by the U.S. Consumer Product Safety Commission.
            Find hazards, affected products, and what to do if your product is recalled.
          </p>

          <form onSubmit={handleSearch} role="search" aria-label="Search recalls">
            <div className="search-bar">
              <label htmlFor="recall-search" className="usa-sr-only">
                Search recalls by product, brand, or hazard
              </label>
              <input
                id="recall-search"
                type="search"
                placeholder="Search by product, brand, hazard..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search recalls"
              />
              <button type="submit" disabled={searching} aria-label="Search">
                {searching ? "Searching..." : "Search"}
              </button>
              <button
                type="button"
                onClick={goToChat}
                style={{ background: "#1a5e1a", borderRadius: 6, padding: "0.65rem 1.1rem", color: "#fff", border: "none", fontWeight: 600, cursor: "pointer" }}
                aria-label="Ask the AI assistant about this recall"
              >
                Ask AI
              </button>
            </div>
          </form>

          {/* Quick stats */}
          <div style={{ display: "flex", gap: "2rem", marginTop: "1.5rem", flexWrap: "wrap" }}>
            {[
              { label: "Active CPSC Recalls", value: "8,000+" },
              { label: "Products in Database", value: "30 yrs" },
              { label: "CPSC Hotline", value: "800-638-2772" },
            ].map((stat) => (
              <div key={stat.label} style={{ color: "rgba(255,255,255,0.85)" }}>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#fff" }}>{stat.value}</div>
                <div style={{ fontSize: ".8rem", opacity: .8 }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Content */}
      <section className="grid-container" style={{ paddingTop: "2rem", paddingBottom: "3rem" }}>

        {/* Filter tabs */}
        {!isSearchResults && (
          <div role="tablist" aria-label="Filter by product category" style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
            {PRODUCT_FILTERS.map((f) => (
              <button
                key={f.value}
                role="tab"
                aria-selected={productFilter === f.value}
                onClick={() => setProductFilter(f.value)}
                style={{
                  padding: ".35rem .9rem",
                  border: "1.5px solid",
                  borderRadius: 999,
                  fontSize: ".875rem",
                  cursor: "pointer",
                  fontWeight: productFilter === f.value ? 700 : 400,
                  borderColor: productFilter === f.value ? "#005288" : "#c9c9c9",
                  background: productFilter === f.value ? "#005288" : "#fff",
                  color: productFilter === f.value ? "#fff" : "#1b1b1b",
                  transition: "all .1s",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}

        {/* Section heading */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: ".5rem" }}>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#1b1b1b", margin: 0 }}>
            {isSearchResults
              ? `Search results for "${query}" (${recalls.length} found)`
              : "Latest CPSC Recalls"}
          </h2>
          {isSearchResults && (
            <button
              onClick={loadLatest}
              style={{ fontSize: ".85rem", color: "#005288", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
            >
              Clear search
            </button>
          )}
        </div>

        {/* Alert */}
        <div className="recall-alert" role="note">
          <strong>Safety tip:</strong> If you have an affected product, stop using it immediately and follow the remedy instructions.
          Call the CPSC hotline at <a href="tel:800-638-2772">800-638-2772</a> for assistance.
        </div>

        {/* Cards */}
        {loading || searching ? (
          <div className="usa-alert usa-alert--info" role="status" aria-live="polite">
            <div className="usa-alert__body">
              <p className="usa-alert__text">Loading recalls...</p>
            </div>
          </div>
        ) : recalls.length === 0 ? (
          <div className="usa-alert usa-alert--warning">
            <div className="usa-alert__body">
              <p className="usa-alert__text">
                No recalls found.{" "}
                <button
                  onClick={goToChat}
                  style={{ color: "#005288", background: "none", border: "none", cursor: "pointer", textDecoration: "underline", fontSize: "inherit" }}
                >
                  Try asking the AI assistant
                </button>{" "}
                for more specific queries.
              </p>
            </div>
          </div>
        ) : (
          <div className="recalls-grid">
            {recalls
              .filter((r) => !productFilter || (r.product_type?.toLowerCase().includes(productFilter) || r.title.toLowerCase().includes(productFilter)))
              .map((recall) => (
                <RecallCard key={recall.id} recall={recall} />
              ))}
          </div>
        )}

        {/* CTA */}
        <div style={{ marginTop: "2.5rem", textAlign: "center" }}>
          <p style={{ color: "#565c65", marginBottom: "1rem" }}>
            Can&apos;t find what you&apos;re looking for? Our AI assistant can answer detailed questions.
          </p>
          <a href="/chat" className="usa-button">
            Ask the Recall Assistant
          </a>
        </div>
      </section>
    </>
  );
}

function RecallCard({ recall }: { recall: Recall }) {
  const date = recall.recall_date
    ? new Date(recall.recall_date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
    : null;

  return (
    <article className="recall-card" aria-labelledby={`recall-title-${recall.id}`}>
      <div className="recall-card__agency" aria-label={`Agency: ${recall.agency_code}`}>
        <svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        CPSC
      </div>

      <h3 className="recall-card__title" id={`recall-title-${recall.id}`}>
        {recall.title}
      </h3>

      <p className="recall-card__meta">
        {[
          recall.brand_name,
          recall.manufacturer,
          date,
          recall.units_affected ? `${recall.units_affected.toLocaleString()} units` : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>

      {recall.hazard && (
        <p className="recall-card__hazard" role="note" aria-label="Hazard">
          <strong>Hazard:</strong> {recall.hazard}
        </p>
      )}

      {recall.remedy && (
        <p className="recall-card__remedy" role="note" aria-label="Remedy">
          <strong>Remedy:</strong> {recall.remedy}
        </p>
      )}

      {recall.url && (
        <a
          className="recall-card__link"
          href={recall.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`More details about ${recall.title} (opens in new tab)`}
        >
          Full recall details
          <svg aria-hidden="true" focusable="false" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginLeft: 4 }}>
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </a>
      )}
    </article>
  );
}
