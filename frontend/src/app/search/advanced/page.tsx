"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RecallCard } from "@/components/RecallCard";
import {
  getFilteredRecalls,
  type Recall,
  type RecallFilterParams,
} from "@/lib/api";

function AdvancedSearchInner() {
  const searchParams = useSearchParams();
  const [recalls, setRecalls] = useState<Recall[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [agencyCode, setAgencyCode] = useState("CPSC");
  const [country, setCountry] = useState("");
  const [brand, setBrand] = useState("");
  const [productType, setProductType] = useState("");
  const [keywords, setKeywords] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(
    async (params: RecallFilterParams) => {
      setLoading(true);
      setError(null);
      try {
        const data = await getFilteredRecalls({
          ...params,
          limit: params.limit ?? 60,
          offset: params.offset ?? 0,
        });
        setRecalls(data.recalls);
        setTotal(data.total);
      } catch {
        setError("Could not load recalls. Check that the API is running.");
        setRecalls([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    const c = searchParams.get("country") ?? "";
    const b = searchParams.get("brand") ?? "";
    const pt = searchParams.get("product_type") ?? "";
    const s = searchParams.get("search") ?? searchParams.get("q") ?? "";
    const df = searchParams.get("date_from") ?? "";
    const dt = searchParams.get("date_to") ?? "";
    const ag = searchParams.get("agency_code") ?? "CPSC";

    setCountry(c);
    setBrand(b);
    setProductType(pt);
    setKeywords(s);
    setDateFrom(df);
    setDateTo(dt);
    setAgencyCode(ag);

    void load({
      agency_code: ag.trim() ? ag : undefined,
      country: c || undefined,
      brand: b || undefined,
      product_type: pt || undefined,
      search: s || undefined,
      date_from: df || undefined,
      date_to: dt || undefined,
      limit: 60,
      offset: 0,
    });
  }, [searchParams, load]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const sp = new URLSearchParams();
    if (agencyCode.trim()) sp.set("agency_code", agencyCode.trim());
    if (country.trim()) sp.set("country", country.trim());
    if (brand.trim()) sp.set("brand", brand.trim());
    if (productType.trim()) sp.set("product_type", productType.trim());
    if (keywords.trim()) sp.set("search", keywords.trim());
    if (dateFrom) sp.set("date_from", dateFrom);
    if (dateTo) sp.set("date_to", dateTo);
    const qs = sp.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : "/search/advanced");
    void load({
      agency_code: agencyCode.trim() || undefined,
      country: country.trim() || undefined,
      brand: brand.trim() || undefined,
      product_type: productType.trim() || undefined,
      search: keywords.trim() || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      limit: 60,
      offset: 0,
    });
  };

  return (
    <main id="main-content" className="grid-container" style={{ paddingTop: "2rem", paddingBottom: "3rem" }}>
      <nav aria-label="Breadcrumb" style={{ marginBottom: "1rem", fontSize: ".85rem" }}>
        <Link href="/search" style={{ color: "#005288" }}>
          Search
        </Link>
        <span style={{ color: "#565c65", margin: "0 .35rem" }}>/</span>
        <span style={{ color: "#1b1b1b" }}>Advanced</span>
      </nav>

      <h1 style={{ fontSize: "1.75rem", marginTop: 0, color: "#1b1b1b" }}>Advanced search</h1>
      <p style={{ color: "#565c65", maxWidth: "42rem", lineHeight: 1.5 }}>
        Filter recalls by agency, manufacturer country, brand, product type, date range, and keywords.
        URLs are shareable for deep links from the assistant.
      </p>

      <form
        onSubmit={onSubmit}
        style={{
          marginTop: "1.5rem",
          padding: "1.25rem",
          background: "#f7f9fa",
          border: "1px solid #dfe1e2",
          borderRadius: 8,
          display: "grid",
          gap: "1rem",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          alignItems: "end",
        }}
      >
        <div>
          <label htmlFor="adv-agency" className="usa-label" style={{ marginTop: 0 }}>
            Agency
          </label>
          <input
            id="adv-agency"
            className="usa-input"
            value={agencyCode}
            onChange={(e) => setAgencyCode(e.target.value)}
            placeholder="CPSC"
            aria-label="Agency code"
          />
        </div>
        <div>
          <label htmlFor="adv-country" className="usa-label" style={{ marginTop: 0 }}>
            Manufacturer country
          </label>
          <input
            id="adv-country"
            className="usa-input"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="e.g. China"
            aria-label="Manufacturer country contains"
          />
        </div>
        <div>
          <label htmlFor="adv-brand" className="usa-label" style={{ marginTop: 0 }}>
            Brand
          </label>
          <input
            id="adv-brand"
            className="usa-input"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            placeholder="Contains…"
            aria-label="Brand name contains"
          />
        </div>
        <div>
          <label htmlFor="adv-ptype" className="usa-label" style={{ marginTop: 0 }}>
            Product type
          </label>
          <input
            id="adv-ptype"
            className="usa-input"
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
            placeholder="e.g. Toy"
            aria-label="Product type contains"
          />
        </div>
        <div>
          <label htmlFor="adv-from" className="usa-label" style={{ marginTop: 0 }}>
            Recall date from
          </label>
          <input
            id="adv-from"
            type="date"
            className="usa-input"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            aria-label="Recall date from"
          />
        </div>
        <div>
          <label htmlFor="adv-to" className="usa-label" style={{ marginTop: 0 }}>
            Recall date to
          </label>
          <input
            id="adv-to"
            type="date"
            className="usa-input"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            aria-label="Recall date to"
          />
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="adv-q" className="usa-label" style={{ marginTop: 0 }}>
            Keywords
          </label>
          <input
            id="adv-q"
            className="usa-input"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="Title, description, hazard, product, manufacturer…"
            aria-label="Keyword search"
          />
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <button type="submit" className="usa-button">
            Apply filters
          </button>
        </div>
      </form>

      <section aria-live="polite" style={{ marginTop: "2rem" }}>
        {loading ? (
          <p style={{ color: "#565c65" }}>Loading…</p>
        ) : error ? (
          <p role="alert" style={{ color: "#b50909" }}>
            {error}
          </p>
        ) : (
          <>
            <p style={{ color: "#565c65", fontSize: ".9rem", marginBottom: "1rem" }}>
              Showing {recalls.length} of {total} matching recalls
            </p>
            {recalls.length === 0 ? (
              <p style={{ color: "#565c65" }}>No recalls match these filters.</p>
            ) : (
              <div
                role="list"
                aria-label="Filtered recalls"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                  gap: "1rem",
                  justifyItems: "stretch",
                }}
              >
                {recalls.map((r) => (
                  <RecallCard key={r.id} recall={r} variant="grid" />
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}

export default function AdvancedSearchPage() {
  return (
    <Suspense fallback={<div className="grid-container" style={{ padding: "2rem" }}>Loading…</div>}>
      <AdvancedSearchInner />
    </Suspense>
  );
}
