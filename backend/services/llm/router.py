"""
Intent router — classifies chat questions and dispatches to the right tool.

Intents:
  rag     → semantic vector search (product/brand/hazard lookups)
  count   → SQL aggregate returning a number
  chart   → SQL aggregate returning chart-able data
"""
import re
import logging
from typing import Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from services.llm.tools import (
    count_recalls,
    recalls_by_period,
    recalls_by_brand,
    recalls_by_company,
    recalls_by_product_type,
    recalls_by_country,
)

logger = logging.getLogger(__name__)

# ── Patterns ──────────────────────────────────────────────────────────────────

_COUNT_RE   = re.compile(r'\b(how many|count|number of|total|quantity)\b', re.I)
_CHART_RE   = re.compile(r'\b(chart|graph|plot|histogram|bar|trend|visuali[sz]e|show me a|distribution)\b', re.I)
_PERIOD_RE  = re.compile(r'\b(by month|monthly|by year|yearly|annual|over time|per month|per year)\b', re.I)
_BRAND_RE   = re.compile(r'\bby brand\b', re.I)
_COMPANY_RE = re.compile(r'\b(by company|by manufacturer|by maker)\b', re.I)
_TYPE_RE    = re.compile(r'\b(by (product )?type|by category|by hazard)\b', re.I)
_COUNTRY_RE = re.compile(r'\b(by country|country of origin|chinese|from china|made in)\b', re.I)

_COUNTRY_MAP = {
    "chinese": "China", "china": "China",
    "japanese": "Japan", "japan": "Japan",
    "korean": "Korea", "korea": "Korea",
    "german": "Germany", "germany": "Germany",
    "american": "United States", "usa": "United States",
}

_MONTHS_PATTERNS = [
    (re.compile(r'\b(last|past)\s+year\b|\b12\s+months\b', re.I), 12),
    (re.compile(r'\b(last|past)\s+6\s+months\b', re.I), 6),
    (re.compile(r'\b(last|past)\s+3\s+months\b|\bquarter\b', re.I), 3),
]


def _extract_months(text: str) -> int:
    for pattern, n in _MONTHS_PATTERNS:
        if pattern.search(text):
            return n
    m = re.search(r'\b(last|past)\s+(\d+)\s+months?\b', text, re.I)
    if m:
        return int(m.group(2))
    return 6


def classify_intent(question: str) -> str:
    if _CHART_RE.search(question) or _PERIOD_RE.search(question):
        return "chart"
    if _COUNT_RE.search(question):
        return "count"
    return "rag"


def _build_date_range(question: str) -> tuple[Optional[date], Optional[date]]:
    """Parse 'last N months' or 'last year' into (date_from, date_to)."""
    from services.llm.tools import _months_ago
    months = _extract_months(question)
    return _months_ago(months), None


async def dispatch_sql_tool(question: str, db: AsyncSession) -> dict:
    """
    Decide which SQL tool to run based on the question and return its result dict.
    Result always has 'tool' key; chart queries also include a 'chart' key.
    """
    months = _extract_months(question)
    use_months = months if not (months == 6 and not re.search(r'\b6\b', question)) else None

    # Country-specific queries
    if _COUNTRY_RE.search(question):
        # Count for a specific country
        country_match = re.search(r'\b(chinese|china|japanese|japan|korean|korea|german|germany|american|usa)\b', question, re.I)
        if country_match and _COUNT_RE.search(question):
            country = _COUNTRY_MAP.get(country_match.group(1).lower(), country_match.group(1))
            date_from, date_to = _build_date_range(question) if re.search(r'\blast\b|\bpast\b', question, re.I) else (None, None)
            return await count_recalls(db, country=country, date_from=date_from, date_to=date_to)
        return await recalls_by_country(db)

    # Time-series / trend
    if _PERIOD_RE.search(question):
        group_by = "year" if re.search(r'\bby year\b|\byearly\b|\bannual\b', question, re.I) else "month"
        return await recalls_by_period(db, group_by=group_by, months=months)

    # By company / manufacturer
    if _COMPANY_RE.search(question):
        return await recalls_by_company(db, months=use_months)

    # By brand
    if _BRAND_RE.search(question):
        return await recalls_by_brand(db, months=use_months)

    # By product type / category
    if _TYPE_RE.search(question):
        return await recalls_by_product_type(db, months=use_months)

    # Generic count — apply date range if mentioned
    if _COUNT_RE.search(question):
        date_from, date_to = _build_date_range(question) if re.search(r'\blast\b|\bpast\b|\bmonth\b|\byear\b', question, re.I) else (None, None)
        return await count_recalls(db, date_from=date_from, date_to=date_to)

    # Fallback — period chart
    return await recalls_by_period(db, months=months)


def format_tool_context(result: dict) -> str:
    """Convert a SQL tool result into a natural-language context string for the LLM."""
    tool = result.get("tool", "")

    if tool == "count_recalls":
        filters = result.get("filters", {})
        filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items()) if filters else "all agencies"
        return f"Query result: {result['count']} recalls found ({filter_desc})."

    labels = result.get("labels", [])
    data = result.get("data", [])
    if not labels:
        return "No data found for this query."

    rows = "\n".join(f"  {label}: {count}" for label, count in zip(labels, data))
    chart = result.get("chart", {})
    title = chart.get("title", tool)
    return f"{title}:\n{rows}"
