# Advanced search from chat (deep links)

When the assistant cites a **count** (e.g. “127 recalls involving Chinese manufacturers”), link that number to **`/search/advanced`** (or a similar route) so users can open the underlying result set.

## Goals

- Numbers in aggregate answers become actionable links to a dedicated **advanced search** view.
- That page loads with **query parameters** reflecting the filters used for the answer (e.g. manufacturer country = China).
- Results use the **same card layout** as the homepage “latest recalls” section.

## Implementation plan

| Step | Work |
|------|------|
| 1. **Query params** | Define a stable contract, e.g. `?country=China&source=manufacturer` or `?q=...` — mirror filters the SQL tools already use (`manufacturer_countries`, date range, agency). |
| 2. **Backend** | Add `GET /api/recalls/filter` (or extend `/api/recalls/search`) that accepts structured filters and returns the same recall shape as `/api/recalls/latest` (pagination optional). Reuse DB conditions from `services/llm/tools.py` where possible. |
| 3. **Advanced search page** | New Next.js route that reads params on mount, calls the filter API, shows the **same card layout** as the homepage “latest recalls” section (extract shared `<RecallCard>` if needed). |
| 4. **Chat UI** | Post-process assistant markdown/HTML or a small structured block from the API (e.g. `{ "explore": { "count": 127, "href": "/search/advanced?country=China" } }`) so the model does not have to invent URLs — **preferred**: backend adds `metadata.explore_url` on SQL-tool responses; frontend wraps matching numbers in `<Link>`. |
| 5. **Accessibility** | Link text describes destination (“View 127 matching recalls”) not just “127”. |

## Related fixes (done)

- **Duplicate chat replies:** The SSE parser was calling `onDone` for any empty `data:` line, not only `event: done`, which appended the assistant message twice. Fixed in `frontend/src/lib/api.ts` (only finalize on `event: done`).
