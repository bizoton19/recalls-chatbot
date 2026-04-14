"use client";

import { useState } from "react";
import type { Recall } from "@/lib/api";

export function RecallCard({
  recall,
  variant = "carousel",
}: {
  recall: Recall;
  variant?: "carousel" | "grid";
}) {
  const [imgError, setImgError] = useState(false);

  const date = recall.recall_date
    ? new Date(recall.recall_date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  const product = recall.product_name || recall.brand_name || recall.product_type || null;
  const agency = recall.agency_code || "CPSC";

  return (
    <article
      role="listitem"
      style={{
        ...(variant === "carousel"
          ? { flex: "0 0 260px", scrollSnapAlign: "start" as const }
          : { width: "100%", maxWidth: 320, justifySelf: "stretch" }),
        background: "#fff",
        border: "1px solid #dfe1e2",
        borderRadius: 8,
        overflow: "hidden",
        boxShadow: "0 1px 4px rgba(0,0,0,.08)",
        display: "flex",
        flexDirection: "column",
        transition: "box-shadow .15s, transform .15s",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 16px rgba(0,0,0,.14)";
        (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 4px rgba(0,0,0,.08)";
        (e.currentTarget as HTMLElement).style.transform = "";
      }}
    >
      <div
        style={{
          width: "100%",
          aspectRatio: "4/3",
          background: "#f0f4f7",
          position: "relative",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        {recall.image_url && !imgError ? (
          <img
            src={recall.image_url}
            alt={product || recall.title}
            onError={() => setImgError(true)}
            draggable={false}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <PlaceholderImage />
        )}
        <div
          style={{
            position: "absolute",
            top: 8,
            left: 8,
            background: "rgba(0,82,136,.9)",
            color: "#fff",
            fontSize: ".65rem",
            fontWeight: 700,
            letterSpacing: ".06em",
            padding: "2px 7px",
            borderRadius: 3,
          }}
        >
          {agency}
        </div>
      </div>

      <div
        style={{
          padding: "0.85rem 0.9rem 0.75rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.35rem",
          flex: 1,
        }}
      >
        <p
          style={
            {
              margin: 0,
              fontSize: ".8rem",
              fontWeight: 700,
              color: "#1b1b1b",
              lineHeight: 1.4,
              display: "-webkit-box",
              WebkitLineClamp: 3,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            } as React.CSSProperties
          }
        >
          {recall.title}
        </p>

        <div style={{ fontSize: ".72rem", color: "#565c65", marginTop: 2 }}>
          {product && (
            <span
              style={{
                display: "block",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {product}
            </span>
          )}
          {date && <span>{date}</span>}
        </div>

        <div style={{ flex: 1 }} />

        {recall.url ? (
          <a
            href={recall.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Full recall details for ${recall.title} (opens agency site)`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: ".75rem",
              color: "#005288",
              fontWeight: 600,
              textDecoration: "none",
              marginTop: "0.5rem",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
            onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
          >
            Full details on CPSC.gov
            <svg
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              aria-hidden="true"
            >
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        ) : null}
      </div>
    </article>
  );
}

function PlaceholderImage() {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#e8f1f7",
      }}
    >
      <svg
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#9eb8cc"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    </div>
  );
}
