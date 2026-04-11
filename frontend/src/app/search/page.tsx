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

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Feature flag hook — checks backend for image search availability
// ---------------------------------------------------------------------------

function useImageSearchEnabled() {
  const [enabled, setEnabled] = useState<boolean | null>(null); // null = loading

  useEffect(() => {
    fetch(`${API_URL}/api/search/status`)
      .then((r) => r.json())
      .then((d) => setEnabled(!!d.image_search))
      .catch(() => setEnabled(false));
  }, []);

  return enabled;
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
  enabled: boolean;
}

function UploadPanel({
  onSearch,
  isSearching,
  preview,
  onPreviewClear,
  visionDescription,
  enabled,
}: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => setPendingFile(file);

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

  const localPreview = pendingFile ? URL.createObjectURL(pendingFile) : null;
  const displayPreview = localPreview || preview;

  return (
    <div className="upload-panel">
      <div className="upload-panel__header">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          aria-hidden="true"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
        Image Search
        {!enabled && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: ".7rem",
              fontWeight: 600,
              background: "#e5e5e5",
              color: "#565c65",
              padding: ".15rem .45rem",
              borderRadius: 4,
              letterSpacing: ".04em",
            }}
          >
            COMING SOON
          </span>
        )}
      </div>

      <div className="upload-panel__body">
        {!enabled ? (
          /* Disabled state */
          <div
            style={{
              padding: "2rem 1rem",
              textAlign: "center",
              background: "#f5f5f5",
              borderRadius: 6,
              border: "1.5px dashed #c9c9c9",
            }}
          >
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#adb5bd"
              strokeWidth="1.5"
              style={{ display: "block", margin: "0 auto .75rem" }}
              aria-hidden="true"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <p
              style={{
                margin: 0,
                color: "#565c65",
                fontSize: ".875rem",
                fontWeight: 600,
              }}
            >
              Image search is not enabled yet.
            </p>
            <p
              style={{
                margin: ".5rem 0 0",
                color: "#71767a",
                fontSize: ".8rem",
                lineHeight: 1.5,
              }}
            >
              Sign up at{" "}
              <a
                href="https://jina.ai"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "#005288" }}
              >
                jina.ai
              </a>{" "}
              and add <code>JINA_API_KEY</code> to enable visual product search.
            </p>
          </div>
        ) : (
          /* Active upload UI */
          <>
            {displayPreview ? (
              <div style={{ position: "relative", marginBottom: ".75rem" }}>
                <img
                  src={displayPreview}
                  alt="Preview of uploaded image"
                  className="upload-preview"
                />
                <button
                  onClick={() => {
                    setPendingFile(null);
                    onPreviewClear();
                  }}
                  style={{
                    position: "absolute",
                    top: 6,
                    right: 6,
                    background: "rgba(0,0,0,.6)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "50%",
                    width: 26,
                    height: 26,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: ".85rem",
                  }}
                  aria-label="Remove image"
                >
                  ×
                </button>
              </div>
            ) : (
              <div
                className={`upload-dropzone ${dragOver ? "drag-over" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                role="button"
                aria-label="Upload an image to search for recalled products"
                tabIndex={0}
                onKeyDown={(e) =>
                  e.key === "Enter" && inputRef.current?.click()
                }
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleInputChange}
                  aria-hidden="true"
                  tabIndex={-1}
                />
                <svg
                  className="upload-dropzone__icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  aria-hidden="true"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <p
                  style={{
                    margin: 0,
                    color: "#565c65",
                    fontSize: ".875rem",
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Drop a product photo here</strong>
                  <br />
                  or click to browse
                </p>
                <p
                  style={{
                    margin: ".5rem 0 0",
                    color: "#71767a",
                    fontSize: ".78rem",
                  }}
                >
                  JPEG, PNG, WebP · up to 10 MB
                </p>
              </div>
            )}

            <button
              className="upload-btn"
              onClick={() => pendingFile && onSearch(pendingFile)}
              disabled={!pendingFile || isSearching}
              aria-label="Search for recalled products matching this image"
            >
              {isSearching ? (
                <>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    style={{ animation: "spin 1s linear infinite" }}
                    aria-hidden="true"
                  >
                    <path
                      d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                      strokeOpacity=".3"
                    />
                    <path d="M21 12a9 9 0 0 0-9-9" />
                  </svg>
                  Searching...
                </>
              ) : (
                <>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    aria-hidden="true"
                  >
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  Search by Image
                </>
              )}
            </button>

            {visionDescription && (
              <div
                className="vision-label"
                role="note"
                aria-label="AI product description"
              >
                <strong>AI detected:</strong> {visionDescription}
              </div>
            )}
          </>
        )}

        <p
          style={{
            fontSize: ".78rem",
            color: "#71767a",
            marginTop: ".75rem",
            lineHeight: 1.5,
          }}
        >
          When enabled, our AI identifies the product in your photo and searches
          CPSC&apos;s recall database for visual and semantic matches.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results panel (right side) — text search only for now
// ---------------------------------------------------------------------------

interface ResultsPanelProps {
  results: UnifiedSearchResult | null;
  loading: boolean;
  query: string;
  imageSearchEnabled: boolean;
}

function ResultsPanel({
  results,
  loading,
  query,
  imageSearchEnabled,
}: ResultsPanelProps) {
  const imageCount = results?.images?.length ?? 0;
  const recallCount = results?.recalls?.length ?? 0;
  const [selectedImage, setSelectedImage] = useState<ImageResult | null>(null);
  const [activeTab, setActiveTab] = useState<"recalls" | "images">("recalls");

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 300,
          color: "#565c65",
        }}
      >
        <p>Searching recalls...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: 300,
          color: "#71767a",
          gap: ".75rem",
        }}
      >
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity=".4"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <p style={{ margin: 0 }}>
          Enter a search term above to find recalls.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Tabs — image tab only shown when image search is active */}
      <div className="result-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "recalls"}
          className={`result-tab ${activeTab === "recalls" ? "active" : ""}`}
          onClick={() => setActiveTab("recalls")}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden="true"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Recall Cards
          <span className="badge">{recallCount}</span>
        </button>

        {imageSearchEnabled && (
          <button
            role="tab"
            aria-selected={activeTab === "images"}
            className={`result-tab ${activeTab === "images" ? "active" : ""}`}
            onClick={() => setActiveTab("images")}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              aria-hidden="true"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            Image Results
            <span className="badge">{imageCount}</span>
          </button>
        )}
      </div>

      {/* Recall cards */}
      {activeTab === "recalls" &&
        (recallCount === 0 ? (
          <div className="usa-alert usa-alert--warning">
            <div className="usa-alert__body">
              <p className="usa-alert__text">
                No recall records matched this search. Try different keywords or{" "}
                <a href="/chat">ask the AI assistant</a>.
              </p>
            </div>
          </div>
        ) : (
          <div className="recalls-grid">
            {results.recalls.map((recall) => {
              const date = recall.recall_date
                ? new Date(recall.recall_date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })
                : null;
              return (
                <article
                  key={recall.id}
                  className="recall-card"
                  aria-labelledby={`recall-${recall.id}`}
                >
                  <div className="recall-card__agency">CPSC</div>
                  <h3
                    className="recall-card__title"
                    id={`recall-${recall.id}`}
                  >
                    {recall.title}
                  </h3>
                  <p className="recall-card__meta">
                    {[recall.brand_name, recall.manufacturer, date]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {recall.hazard && (
                    <p className="recall-card__hazard">
                      <strong>Hazard:</strong> {recall.hazard}
                    </p>
                  )}
                  {recall.remedy && (
                    <p className="recall-card__remedy">
                      <strong>Remedy:</strong> {recall.remedy}
                    </p>
                  )}
                  {recall.url && (
                    <a
                      className="recall-card__link"
                      href={recall.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Full recall details
                    </a>
                  )}
                </article>
              );
            })}
          </div>
        ))}

      {/* Image results (only rendered when Jina enabled) */}
      {activeTab === "images" && imageSearchEnabled && (
        imageCount === 0 ? (
          <div className="usa-alert usa-alert--info">
            <div className="usa-alert__body">
              <p className="usa-alert__text">
                No product images matched this search.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div
              className="image-grid"
              role="list"
              aria-label={`${imageCount} image results`}
            >
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
                      (e.target as HTMLImageElement).parentElement!.style.display =
                        "none";
                    }}
                  />
                  <div className="image-tile__similarity">
                    {Math.round(img.similarity * 100)}%
                  </div>
                  <div className="image-tile__label">
                    {img.brand_name || img.title}
                  </div>
                </article>
              ))}
            </div>

            {selectedImage && (
              <div
                style={{
                  position: "fixed",
                  inset: 0,
                  background: "rgba(0,0,0,.6)",
                  zIndex: 1000,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "1rem",
                }}
                onClick={() => setSelectedImage(null)}
                role="dialog"
                aria-modal="true"
                aria-label={`Recall details: ${selectedImage.title}`}
              >
                <div
                  style={{
                    background: "#fff",
                    borderRadius: 6,
                    maxWidth: 560,
                    width: "100%",
                    padding: "1.5rem",
                    boxShadow: "0 20px 60px rgba(0,0,0,.3)",
                    position: "relative",
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => setSelectedImage(null)}
                    style={{
                      position: "absolute",
                      top: 12,
                      right: 12,
                      background: "none",
                      border: "none",
                      fontSize: "1.25rem",
                      cursor: "pointer",
                      color: "#565c65",
                    }}
                    aria-label="Close"
                  >
                    ×
                  </button>
                  <img
                    src={selectedImage.image_url}
                    alt={selectedImage.alt_text || selectedImage.title}
                    style={{
                      width: "100%",
                      maxHeight: 240,
                      objectFit: "contain",
                      background: "#f5f5f5",
                      borderRadius: 4,
                      marginBottom: "1rem",
                    }}
                  />
                  <h2
                    style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 .5rem" }}
                  >
                    {selectedImage.title}
                  </h2>
                  <p style={{ fontSize: ".85rem", color: "#565c65", margin: "0 0 .75rem" }}>
                    {selectedImage.brand_name} ·{" "}
                    {selectedImage.recall_date
                      ? new Date(selectedImage.recall_date).toLocaleDateString(
                          "en-US",
                          { year: "numeric", month: "short" }
                        )
                      : ""}{" "}
                    · Match: {Math.round(selectedImage.similarity * 100)}%
                  </p>
                  {selectedImage.hazard && (
                    <p
                      style={{
                        fontSize: ".875rem",
                        color: "#c1272d",
                        background: "#fff3f3",
                        borderLeft: "3px solid #c1272d",
                        padding: ".4rem .65rem",
                        borderRadius: "0 4px 4px 0",
                        margin: "0 0 .5rem",
                      }}
                    >
                      <strong>Hazard:</strong> {selectedImage.hazard}
                    </p>
                  )}
                  {selectedImage.remedy && (
                    <p
                      style={{
                        fontSize: ".875rem",
                        color: "#1a6e2e",
                        background: "#f0faf2",
                        borderLeft: "3px solid #1a6e2e",
                        padding: ".4rem .65rem",
                        borderRadius: "0 4px 4px 0",
                        margin: "0 0 .75rem",
                      }}
                    >
                      <strong>Remedy:</strong> {selectedImage.remedy}
                    </p>
                  )}
                  {selectedImage.recall_url && (
                    <a
                      href={selectedImage.recall_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: ".875rem",
                        color: "#005288",
                        textDecoration: "underline",
                      }}
                    >
                      View full recall on CPSC.gov
                    </a>
                  )}
                </div>
              </div>
            )}
          </>
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
  const imageSearchEnabled = useImageSearchEnabled();

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<UnifiedSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [visionDescription, setVisionDescription] = useState<string | null>(null);

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
    const url = URL.createObjectURL(file);
    setImagePreview(url);
    setLoading(true);
    setResults(null);
    setVisionDescription(null);
    try {
      const data = await imageSearch(file);
      setResults(data);
      setVisionDescription(data.vision_description || null);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <section
        className="recalls-hero"
        aria-labelledby="search-heading"
        style={{ padding: "2.5rem 0 3rem" }}
      >
        <div className="grid-container">
          <h1
            id="search-heading"
            style={{ fontSize: "1.85rem", marginBottom: ".5rem" }}
          >
            CPSC Recall Search
          </h1>
          <p
            style={{ opacity: 0.9, maxWidth: 520, marginBottom: "1.25rem" }}
          >
            Search CPSC product recalls by keyword. Use the AI assistant for
            detailed questions.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleTextSearch(query);
            }}
            role="search"
            aria-label="Text search for recalls"
          >
            <div className="search-bar" style={{ maxWidth: 560 }}>
              <label htmlFor="text-search" className="usa-sr-only">
                Search recalls by product, brand, or hazard
              </label>
              <input
                id="text-search"
                type="search"
                placeholder="Search by product, brand, or hazard..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" disabled={loading}>
                Search
              </button>
              <a
                href="/chat"
                style={{
                  padding: ".65rem 1.1rem",
                  background: "#1a5e1a",
                  color: "#fff",
                  borderRadius: 6,
                  fontWeight: 600,
                  textDecoration: "none",
                  whiteSpace: "nowrap",
                  fontSize: ".9rem",
                }}
              >
                Ask AI
              </a>
            </div>
          </form>
        </div>
      </section>

      <div className="grid-container">
        <div className="search-page-layout">
          {/* Left: image upload (disabled state shown until Jina is enabled) */}
          <UploadPanel
            onSearch={handleImageSearch}
            isSearching={loading}
            preview={imagePreview}
            onPreviewClear={() => setImagePreview(null)}
            visionDescription={visionDescription}
            enabled={imageSearchEnabled === true}
          />

          {/* Right: results */}
          <ResultsPanel
            results={results}
            loading={loading}
            query={query}
            imageSearchEnabled={imageSearchEnabled === true}
          />
        </div>
      </div>

      <style jsx global>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </>
  );
}
