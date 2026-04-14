"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getLatestRecalls, type Recall } from "@/lib/api";
import { RecallCard } from "@/components/RecallCard";

export default function HomePage() {
  const router = useRouter();
  const [recalls, setRecalls] = useState<Recall[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    getLatestRecalls(15)
      .then((data) => setRecalls(data))
      .catch(() => setRecalls([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
    else router.push("/search");
  };

  const goToChat = () => {
    router.push(query.trim() ? `/chat?q=${encodeURIComponent(query.trim())}` : "/chat");
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
                {searching ? "Searching…" : "Search"}
              </button>
              <button
                type="button"
                onClick={goToChat}
                style={{ background: "#1a5e1a", borderRadius: 6, padding: "0.65rem 1.1rem", color: "#fff", border: "none", fontWeight: 600, cursor: "pointer" }}
                aria-label="Ask the AI assistant"
              >
                Ask AI
              </button>
            </div>
          </form>

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

      {/* Latest Recalls Carousel */}
      <section
        className="grid-container"
        style={{ paddingTop: "2rem", paddingBottom: "3rem" }}
        aria-labelledby="latest-heading"
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <h2 id="latest-heading" style={{ fontSize: "1.15rem", fontWeight: 700, color: "#1b1b1b", margin: 0 }}>
            Latest CPSC Recalls
          </h2>
          <a
            href="/search"
            style={{ fontSize: ".85rem", color: "#005288", textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}
          >
            View all
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </a>
        </div>

        {loading ? (
          <RecallCarouselSkeleton />
        ) : recalls.length === 0 ? (
          <p style={{ color: "#565c65", fontSize: ".9rem" }}>No recalls found yet — data is being indexed.</p>
        ) : (
          <RecallCarousel recalls={recalls} />
        )}

        <div style={{ marginTop: "2rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <a href="/search" className="usa-button usa-button--outline">Search by Image</a>
          <a href="/chat" className="usa-button">Ask the Recall Assistant</a>
        </div>
      </section>
    </>
  );
}

// ---------------------------------------------------------------------------
// Horizontal drag-scroll carousel
// ---------------------------------------------------------------------------

function RecallCarousel({ recalls }: { recalls: Recall[] }) {
  const trackRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollLeft = useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    startX.current = e.pageX - (trackRef.current?.offsetLeft ?? 0);
    scrollLeft.current = trackRef.current?.scrollLeft ?? 0;
    if (trackRef.current) trackRef.current.style.cursor = "grabbing";
  };

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current || !trackRef.current) return;
    e.preventDefault();
    const x = e.pageX - trackRef.current.offsetLeft;
    const walk = (x - startX.current) * 1.2;
    trackRef.current.scrollLeft = scrollLeft.current - walk;
  }, []);

  const onMouseUp = useCallback(() => {
    isDragging.current = false;
    if (trackRef.current) trackRef.current.style.cursor = "grab";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  const scrollBy = (dir: -1 | 1) => {
    trackRef.current?.scrollBy({ left: dir * 300, behavior: "smooth" });
  };

  return (
    <div style={{ position: "relative" }}>
      {/* Left arrow */}
      <CarouselArrow dir="left" onClick={() => scrollBy(-1)} />

      {/* Scrollable track */}
      <div
        ref={trackRef}
        onMouseDown={onMouseDown}
        role="list"
        aria-label="Latest CPSC recalls"
        style={{
          display: "flex",
          gap: "1rem",
          overflowX: "auto",
          scrollSnapType: "x mandatory",
          WebkitOverflowScrolling: "touch",
          paddingBottom: "1rem",
          cursor: "grab",
          userSelect: "none",
          scrollbarWidth: "none",
          msOverflowStyle: "none",
        } as React.CSSProperties}
      >
        {recalls.map((recall) => (
          <RecallCard key={recall.id} recall={recall} variant="carousel" />
        ))}
      </div>

      {/* Right arrow */}
      <CarouselArrow dir="right" onClick={() => scrollBy(1)} />

      <style>{`
        [role="list"]::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}

function CarouselArrow({ dir, onClick }: { dir: "left" | "right"; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-label={dir === "left" ? "Scroll left" : "Scroll right"}
      style={{
        position: "absolute",
        top: "50%",
        transform: "translateY(-60%)",
        [dir === "left" ? "left" : "right"]: -20,
        zIndex: 2,
        background: "#fff",
        border: "1.5px solid #dfe1e2",
        borderRadius: "50%",
        width: 36,
        height: 36,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        boxShadow: "0 2px 8px rgba(0,0,0,.12)",
        padding: 0,
        color: "#005288",
      }}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
        <polyline points={dir === "left" ? "15 18 9 12 15 6" : "9 18 15 12 9 6"} />
      </svg>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function RecallCarouselSkeleton() {
  return (
    <div style={{ display: "flex", gap: "1rem", overflowX: "hidden" }} aria-busy="true" aria-label="Loading recalls">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{ flex: "0 0 260px", borderRadius: 8, overflow: "hidden", border: "1px solid #dfe1e2" }}>
          <div style={{ width: "100%", aspectRatio: "4/3", background: "#e8edf0", animation: "skeleton-pulse 1.4s ease-in-out infinite" }} />
          <div style={{ padding: "0.85rem 0.9rem" }}>
            <div style={{ height: 12, background: "#e8edf0", borderRadius: 4, marginBottom: 8, animation: "skeleton-pulse 1.4s ease-in-out infinite", animationDelay: `${i * .1}s` }} />
            <div style={{ height: 12, background: "#e8edf0", borderRadius: 4, width: "70%", animation: "skeleton-pulse 1.4s ease-in-out infinite", animationDelay: `${i * .1 + .1}s` }} />
          </div>
        </div>
      ))}
      <style>{`
        @keyframes skeleton-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: .4; }
        }
      `}</style>
    </div>
  );
}
