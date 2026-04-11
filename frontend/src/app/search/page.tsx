"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  textSearch,
  imageSearch,
  type Recall,
  type ImageResult,
  type UnifiedSearchResult,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// FBI Shuffle Animation
// ---------------------------------------------------------------------------

interface FBIShuffleProps {
  images: ImageResult[];
  onDone: () => void;
}

function FBIShuffle({ images, onDone }: FBIShuffleProps) {
  const [phase, setPhase] = useState<"shuffle" | "narrow" | "done">("shuffle");
  const [visibleImages, setVisibleImages] = useState<ImageResult[]>([]);
  const [progress, setProgress] = useState(0);
  const [activeIdx, setActiveIdx] = useState(0);
  const [statusText, setStatusText] = useState("SEARCHING DATABASE...");

  // Build a pool: real results + random placeholders to fill 12 slots
  const GRID_SIZE = 12;
  const pool = [...images];
  // Fill remaining slots by cycling through real images or using placeholders
  while (pool.length < GRID_SIZE && images.length > 0) {
    pool.push(images[pool.length % images.length]);
  }

  useEffect(() => {
    if (images.length === 0) { onDone(); return; }

    let tick = 0;
    const totalTicks = 60;

    // Phase 1: rapid shuffle — cycle through images fast
    const shuffleInterval = setInterval(() => {
      tick++;
      setProgress((tick / totalTicks) * 100);
      setActiveIdx(Math.floor(Math.random() * GRID_SIZE));

      if (tick === 20) setStatusText("CROSS-REFERENCING CPSC DATABASE...");
      if (tick === 40) setStatusText("ANALYZING VISUAL SIGNATURE...");

      if (tick >= totalTicks) {
        clearInterval(shuffleInterval);
        setPhase("narrow");
        setStatusText("MATCH IDENTIFIED");
        setVisibleImages(images.slice(0, GRID_SIZE));
        setProgress(100);

        // Pause on "match", then finish
        setTimeout(() => {
          setPhase("done");
          setTimeout(onDone, 600);
        }, 1800);
      }
    }, 60);

    return () => clearInterval(shuffleInterval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const displayImages = phase === "shuffle"
    ? pool
    : visibleImages.length > 0 ? visibleImages : pool;

  return (
    <div className="fbi-shuffle-overlay" role="dialog" aria-label="Searching recall database" aria-live="polite">
      {/* Scanline effect */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,200,255,0.02) 2px, rgba(0,200,255,0.02) 4px)",
      }} />

      <div style={{ fontFamily: "monospace", fontSize: ".75rem", color: "#0066aa", letterSpacing: ".15em", marginBottom: ".25rem" }}>
        CPSC RECALL DATABASE — VISUAL MATCH SYSTEM v2.1
      </div>

      <div className="fbi-shuffle-grid">
        {Array.from({ length: GRID_SIZE }).map((_, i) => {
          const img = displayImages[i % displayImages.length];
          const isMatched = phase === "narrow" && i < images.length;
          const isActive = phase === "shuffle" && i === activeIdx;

          return (
            <div
              key={i}
              className={`fbi-frame ${isActive ? "active" : ""} ${isMatched ? "matched" : ""}`}
            >
              {img?.image_url ? (
                <img
                  src={img.image_url}
                  alt={img.alt_text || img.title}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src =
                      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Crect fill='%230a1520' width='140' height='140'/%3E%3Ctext x='50%25' y='50%25' fill='%23335566' text-anchor='middle' dy='.3em' font-size='10'%3ENO IMAGE%3C/text%3E%3C/svg%3E";
                  }}
                />
              ) : (
                <div style={{ width: "100%", height: "100%", background: "#0a1520", display: "flex", alignItems: "center", justifyContent: "center", color: "#335566", fontSize: ".65rem", fontFamily: "monospace" }}>
                  NO IMAGE
                </div>
              )}
              {isMatched && img && (
                <div className="fbi-score">
                  {Math.round(img.similarity * 100)}%
                </div>
              )}
              {isMatched && phase === "done" && (
                <div className="fbi-matched-label">MATCH</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="fbi-progress-bar">
        <div className="fbi-progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="fbi-status">{statusText}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Image upload panel (left side)
// ---------------------------------------------------------------------------

interface UploadPanelProps {
  onSearch: (file: File) => void;
  isSearching: boolean;
  preview: string | null;
  onPreviewClear: () => void;
  visionDescription: string | null;
}

function UploadPanel({ onSearch, isSearching, preview, onPreviewClear, visionDescription }: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setPendingFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) handleFile(file);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleSearch = () => {
    if (pendingFile) onSearch(pendingFile);
  };

  const localPreview = pendingFile ? URL.createObjectURL(pendingFile) : null;
  const displayPreview = localPreview || preview;

  return (
    <div className="upload-panel">
      <div className="upload-panel__header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        Image Search
      </div>

      <div className="upload-panel__body">
        {displayPreview ? (
          <div style={{ position: "relative", marginBottom: ".75rem" }}>
            <img src={displayPreview} alt="Preview of uploaded image" className="upload-preview" />
            <button
              onClick={() => { setPendingFile(null); onPreviewClear(); }}
              style={{
                position: "absolute", top: 6, right: 6,
                background: "rgba(0,0,0,.6)", color: "#fff", border: "none",
                borderRadius: "50%", width: 26, height: 26, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: ".85rem",
              }}
              aria-label="Remove image"
            >
              ×
            </button>
          </div>
        ) : (
          <div
            className={`upload-dropzone ${dragOver ? "drag-over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            aria-label="Upload an image to search for recalled products"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleInputChange}
              aria-hidden="true"
              tabIndex={-1}
            />
            <svg className="upload-dropzone__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            <p style={{ margin: 0, color: "#565c65", fontSize: ".875rem", lineHeight: 1.5 }}>
              <strong>Drop a product photo here</strong>
              <br />or click to browse
            </p>
            <p style={{ margin: ".5rem 0 0", color: "#71767a", fontSize: ".78rem" }}>
              JPEG, PNG, WebP · up to 10 MB
            </p>
          </div>
        )}

        <button
          className="upload-btn"
          onClick={handleSearch}
          disabled={!pendingFile || isSearching}
          aria-label="Search for recalled products matching this image"
        >
          {isSearching ? (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 1s linear infinite" }} aria-hidden="true">
                <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" strokeOpacity=".3"/>
                <path d="M21 12a9 9 0 0 0-9-9"/>
              </svg>
              Searching...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              Search by Image
            </>
          )}
        </button>

        {visionDescription && (
          <div className="vision-label" role="note" aria-label="AI product description">
            <strong>AI detected:</strong> {visionDescription}
          </div>
        )}

        <p style={{ fontSize: ".78rem", color: "#71767a", marginTop: ".75rem", lineHeight: 1.5 }}>
          Our AI identifies the product in your photo and searches CPSC's recall database for visual and semantic matches.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results panel (right side)
// ---------------------------------------------------------------------------

type ResultTab = "images" | "recalls";

interface ResultsPanelProps {
  results: UnifiedSearchResult | null;
  loading: boolean;
  query: string;
}

function ResultsPanel({ results, loading, query }: ResultsPanelProps) {
  const [activeTab, setActiveTab] = useState<ResultTab>("images");
  const [selectedImage, setSelectedImage] = useState<ImageResult | null>(null);

  const imageCount = results?.images?.length ?? 0;
  const recallCount = results?.recalls?.length ?? 0;

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 300, color: "#565c65" }}>
        <p>Analyzing results...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, color: "#71767a", gap: ".75rem" }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".4" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <p style={{ margin: 0 }}>Upload a product image or enter a search term to find recalls.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Tabs */}
      <div className="result-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "images"}
          className={`result-tab ${activeTab === "images" ? "active" : ""}`}
          onClick={() => setActiveTab("images")}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
          Image Results
          <span className="badge">{imageCount}</span>
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "recalls"}
          className={`result-tab ${activeTab === "recalls" ? "active" : ""}`}
          onClick={() => setActiveTab("recalls")}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Recall Cards
          <span className="badge">{recallCount}</span>
        </button>
      </div>

      {/* Image results tab */}
      {activeTab === "images" && (
        imageCount === 0 ? (
          <div className="usa-alert usa-alert--info">
            <div className="usa-alert__body">
              <p className="usa-alert__text">
                No product images found. Images are indexed during ingestion — run a full sync to populate them.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="image-grid" role="list" aria-label={`${imageCount} image results`}>
              {results.images.map((img) => (
                <article
                  key={img.image_id}
                  className="image-tile"
                  role="listitem"
                  onClick={() => setSelectedImage(img)}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && setSelectedImage(img)}
                  aria-label={`${img.title} — ${Math.round(img.similarity * 100)}% match`}
                >
                  <img
                    src={img.image_url}
                    alt={img.alt_text || img.title}
                    loading="lazy"
                    onError={(e) => {
                      (e.target as HTMLImageElement).parentElement!.style.display = "none";
                    }}
                  />
                  <div className="image-tile__similarity">{Math.round(img.similarity * 100)}%</div>
                  <div className="image-tile__label">{img.brand_name || img.title}</div>
                </article>
              ))}
            </div>

            {/* Detail drawer */}
            {selectedImage && (
              <div
                style={{
                  position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", zIndex: 1000,
                  display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem",
                }}
                onClick={() => setSelectedImage(null)}
                role="dialog"
                aria-modal="true"
                aria-label={`Recall details: ${selectedImage.title}`}
              >
                <div
                  style={{
                    background: "#fff", borderRadius: 6, maxWidth: 560, width: "100%",
                    padding: "1.5rem", boxShadow: "0 20px 60px rgba(0,0,0,.3)", position: "relative",
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => setSelectedImage(null)}
                    style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", fontSize: "1.25rem", cursor: "pointer", color: "#565c65" }}
                    aria-label="Close"
                  >×</button>
                  <img src={selectedImage.image_url} alt={selectedImage.alt_text || selectedImage.title} style={{ width: "100%", maxHeight: 240, objectFit: "contain", background: "#f5f5f5", borderRadius: 4, marginBottom: "1rem" }} />
                  <h2 style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 .5rem" }}>{selectedImage.title}</h2>
                  <p style={{ fontSize: ".85rem", color: "#565c65", margin: "0 0 .75rem" }}>
                    {selectedImage.brand_name} · {selectedImage.recall_date ? new Date(selectedImage.recall_date).toLocaleDateString("en-US", { year: "numeric", month: "short" }) : ""} · Match: {Math.round(selectedImage.similarity * 100)}%
                  </p>
                  {selectedImage.hazard && <p style={{ fontSize: ".875rem", color: "#c1272d", background: "#fff3f3", borderLeft: "3px solid #c1272d", padding: ".4rem .65rem", borderRadius: "0 4px 4px 0", margin: "0 0 .5rem" }}><strong>Hazard:</strong> {selectedImage.hazard}</p>}
                  {selectedImage.remedy && <p style={{ fontSize: ".875rem", color: "#1a6e2e", background: "#f0faf2", borderLeft: "3px solid #1a6e2e", padding: ".4rem .65rem", borderRadius: "0 4px 4px 0", margin: "0 0 .75rem" }}><strong>Remedy:</strong> {selectedImage.remedy}</p>}
                  {selectedImage.recall_url && (
                    <a href={selectedImage.recall_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: ".875rem", color: "#005288", textDecoration: "underline" }}>
                      View full recall on CPSC.gov →
                    </a>
                  )}
                </div>
              </div>
            )}
          </>
        )
      )}

      {/* Recall cards tab */}
      {activeTab === "recalls" && (
        recallCount === 0 ? (
          <div className="usa-alert usa-alert--warning">
            <div className="usa-alert__body">
              <p className="usa-alert__text">No recall records matched this search.</p>
            </div>
          </div>
        ) : (
          <div className="recalls-grid">
            {results.recalls.map((recall) => {
              const date = recall.recall_date ? new Date(recall.recall_date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : null;
              return (
                <article key={recall.id} className="recall-card" aria-labelledby={`recall-${recall.id}`}>
                  <div className="recall-card__agency">CPSC</div>
                  <h3 className="recall-card__title" id={`recall-${recall.id}`}>{recall.title}</h3>
                  <p className="recall-card__meta">{[recall.brand_name, recall.manufacturer, date].filter(Boolean).join(" · ")}</p>
                  {recall.hazard && <p className="recall-card__hazard"><strong>Hazard:</strong> {recall.hazard}</p>}
                  {recall.remedy && <p className="recall-card__remedy"><strong>Remedy:</strong> {recall.remedy}</p>}
                  {recall.url && <a className="recall-card__link" href={recall.url} target="_blank" rel="noopener noreferrer">Full recall details</a>}
                </article>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function SearchPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<UnifiedSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [visionDescription, setVisionDescription] = useState<string | null>(null);
  const [showShuffle, setShowShuffle] = useState(false);
  const [shuffleImages, setShuffleImages] = useState<ImageResult[]>([]);

  // Run text search on initial query
  useEffect(() => {
    if (initialQuery) handleTextSearch(initialQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTextSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setResults(null);
    setVisionDescription(null);
    try {
      const data = await textSearch(q);
      setResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleImageSearch = async (file: File) => {
    // Show preview immediately
    const url = URL.createObjectURL(file);
    setImagePreview(url);
    setLoading(true);
    setResults(null);
    setVisionDescription(null);

    try {
      const data = await imageSearch(file);

      // Trigger FBI shuffle if we have image results
      if (data.images && data.images.length > 0) {
        setShuffleImages(data.images);
        setShowShuffle(true);
        setResults(data);
        setVisionDescription(data.vision_description || null);
      } else {
        setResults(data);
        setVisionDescription(data.vision_description || null);
        setLoading(false);
      }
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  const handleShuffleDone = () => {
    setShowShuffle(false);
    setLoading(false);
  };

  return (
    <>
      {/* FBI Shuffle overlay */}
      {showShuffle && (
        <FBIShuffle images={shuffleImages} onDone={handleShuffleDone} />
      )}

      {/* Page header */}
      <section className="recalls-hero" aria-labelledby="search-heading" style={{ padding: "2.5rem 0 3rem" }}>
        <div className="grid-container">
          <h1 id="search-heading" style={{ fontSize: "1.85rem", marginBottom: ".5rem" }}>
            CPSC Recall Search
          </h1>
          <p style={{ opacity: .9, maxWidth: 520, marginBottom: "1.25rem" }}>
            Search by text or upload a product photo. AI identifies the product and cross-references the CPSC recall database.
          </p>

          {/* Text search bar */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleTextSearch(query); }}
            role="search"
            aria-label="Text search for recalls"
          >
            <div className="search-bar" style={{ maxWidth: 560 }}>
              <label htmlFor="text-search" className="usa-sr-only">Search recalls by product, brand, or hazard</label>
              <input
                id="text-search"
                type="search"
                placeholder="Search by product, brand, or hazard..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" disabled={loading}>Search</button>
              <a href="/chat" style={{ padding: ".65rem 1.1rem", background: "#1a5e1a", color: "#fff", borderRadius: 6, fontWeight: 600, textDecoration: "none", whiteSpace: "nowrap", fontSize: ".9rem" }}>Ask AI</a>
            </div>
          </form>
        </div>
      </section>

      {/* Main layout */}
      <div className="grid-container">
        <div className="search-page-layout">
          {/* Left: image upload */}
          <UploadPanel
            onSearch={handleImageSearch}
            isSearching={loading}
            preview={imagePreview}
            onPreviewClear={() => setImagePreview(null)}
            visionDescription={visionDescription}
          />

          {/* Right: results */}
          <ResultsPanel results={results} loading={loading} query={query} />
        </div>
      </div>

      <style jsx global>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        :root { --radius: 6px; }
      `}</style>
    </>
  );
}
