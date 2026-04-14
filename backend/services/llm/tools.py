"""
Safe parameterized SQL tools for aggregate recall queries.
The LLM never writes raw SQL — it calls these typed functions.
"""
import re
from datetime import date
from typing import Optional
from sqlalchemy import func, text, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.recall import Recall
from services.recalls.filter_builder import apply_recall_filters


# ── Chart spec helpers ────────────────────────────────────────────────────────

def bar_chart(title: str, labels: list, data: list, x_label: str = "", y_label: str = "Count") -> dict:
    return {"type": "bar", "title": title, "labels": labels, "data": data,
            "x_label": x_label, "y_label": y_label}


def pie_chart(title: str, labels: list, data: list) -> dict:
    return {"type": "pie", "title": title, "labels": labels, "data": data}


# ── Date helpers ──────────────────────────────────────────────────────────────

def _months_ago(n: int) -> date:
    today = date.today()
    month = today.month - n
    year = today.year + month // 12
    month = month % 12 or 12
    return date(year, month, 1)


# ── Query tools ───────────────────────────────────────────────────────────────

async def count_recalls(
    db: AsyncSession,
    agency_code: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    brand: Optional[str] = None,
    product_type: Optional[str] = None,
    country: Optional[str] = None,
) -> dict:
    """Count recalls matching the given filters."""
    q = select(func.count()).select_from(Recall)
    q = apply_recall_filters(
        q,
        agency_code=agency_code,
        date_from=date_from,
        date_to=date_to,
        brand=brand,
        product_type=product_type,
        country=country,
    )

    result = await db.execute(q)
    count = result.scalar() or 0

    filters = {k: v for k, v in {
        "agency": agency_code, "from": str(date_from) if date_from else None,
        "to": str(date_to) if date_to else None, "brand": brand,
        "product_type": product_type, "country": country,
    }.items() if v}

    return {"tool": "count_recalls", "count": count, "filters": filters}


async def recalls_by_period(
    db: AsyncSession,
    group_by: str = "month",
    months: int = 6,
    agency_code: Optional[str] = None,
) -> dict:
    """Group recalls by month or year over a given window."""
    date_from = _months_ago(months)

    if group_by == "year":
        trunc = func.date_trunc("year", Recall.recall_date)
    elif group_by == "week":
        trunc = func.date_trunc("week", Recall.recall_date)
    else:
        trunc = func.date_trunc("month", Recall.recall_date)

    q = (
        select(trunc.label("period"), func.count().label("count"))
        .where(Recall.recall_date >= date_from)
        .where(Recall.recall_date.isnot(None))
    )
    if agency_code:
        q = q.where(Recall.agency_code == agency_code)
    q = q.group_by("period").order_by("period")

    rows = (await db.execute(q)).fetchall()

    if group_by == "year":
        labels = [r.period.strftime("%Y") for r in rows]
    elif group_by == "week":
        labels = [r.period.strftime("%b %d") for r in rows]
    else:
        labels = [r.period.strftime("%b %Y") for r in rows]

    data = [r.count for r in rows]

    return {
        "tool": "recalls_by_period",
        "labels": labels,
        "data": data,
        "chart": bar_chart(
            title=f"Recalls by {group_by.capitalize()} — Last {months} months",
            labels=labels,
            data=data,
            x_label=group_by.capitalize(),
            y_label="Number of Recalls",
        ),
    }


async def recalls_by_brand(
    db: AsyncSession,
    months: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Top brands by recall count."""
    q = (
        select(Recall.brand_name.label("brand"), func.count().label("count"))
        .where(Recall.brand_name.isnot(None))
        .where(Recall.brand_name != "")
    )
    if months:
        q = q.where(Recall.recall_date >= _months_ago(months))
    q = q.group_by(Recall.brand_name).order_by(func.count().desc()).limit(limit)

    rows = (await db.execute(q)).fetchall()
    labels = [r.brand for r in rows]
    data = [r.count for r in rows]

    return {
        "tool": "recalls_by_brand",
        "labels": labels,
        "data": data,
        "chart": bar_chart(
            title=f"Top {limit} Brands by Recall Count",
            labels=labels,
            data=data,
            y_label="Number of Recalls",
        ),
    }


async def recalls_by_company(
    db: AsyncSession,
    months: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Top manufacturers/companies by recall count."""
    q = (
        select(Recall.manufacturer.label("manufacturer"), func.count().label("count"))
        .where(Recall.manufacturer.isnot(None))
        .where(Recall.manufacturer != "")
    )
    if months:
        q = q.where(Recall.recall_date >= _months_ago(months))
    q = q.group_by(Recall.manufacturer).order_by(func.count().desc()).limit(limit)

    rows = (await db.execute(q)).fetchall()
    labels = [r.manufacturer for r in rows]
    data = [r.count for r in rows]

    return {
        "tool": "recalls_by_company",
        "labels": labels,
        "data": data,
        "chart": bar_chart(
            title=f"Top {limit} Companies by Recall Count",
            labels=labels,
            data=data,
            y_label="Number of Recalls",
        ),
    }


async def recalls_by_product_type(
    db: AsyncSession,
    months: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Top product categories by recall count."""
    q = (
        select(Recall.product_type.label("product_type"), func.count().label("count"))
        .where(Recall.product_type.isnot(None))
        .where(Recall.product_type != "")
    )
    if months:
        q = q.where(Recall.recall_date >= _months_ago(months))
    q = q.group_by(Recall.product_type).order_by(func.count().desc()).limit(limit)

    rows = (await db.execute(q)).fetchall()
    labels = [r.product_type for r in rows]
    data = [r.count for r in rows]

    return {
        "tool": "recalls_by_product_type",
        "labels": labels,
        "data": data,
        "chart": bar_chart(
            title=f"Top {limit} Product Categories by Recall Count",
            labels=labels,
            data=data,
            y_label="Number of Recalls",
        ),
    }


async def recalls_by_country(
    db: AsyncSession,
    limit: int = 10,
) -> dict:
    """Top manufacturer countries by recall count (CPSC ManufacturerCountries)."""
    q = text("""
        SELECT country, COUNT(DISTINCT recall_id) AS count FROM (
            SELECT r.id AS recall_id, trim(x) AS country
            FROM recalls r
            CROSS JOIN LATERAL unnest(COALESCE(r.manufacturer_countries, ARRAY[]::text[])) AS x
            WHERE trim(x) IS NOT NULL AND trim(x) != ''
            UNION ALL
            SELECT r.id, trim(elem->>'Country')
            FROM recalls r
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(r.raw_data->'ManufacturerCountries', '[]'::jsonb)
            ) elem
            WHERE (r.manufacturer_countries IS NULL OR cardinality(r.manufacturer_countries) = 0)
              AND trim(elem->>'Country') IS NOT NULL AND trim(elem->>'Country') != ''
        ) u
        GROUP BY country
        ORDER BY count DESC
        LIMIT :limit
    """).bindparams(limit=limit)

    rows = (await db.execute(q)).fetchall()
    labels = [r.country for r in rows]
    data = [r.count for r in rows]

    return {
        "tool": "recalls_by_country",
        "labels": labels,
        "data": data,
        "chart": bar_chart(
            title=f"Top {limit} Countries of Origin by Recall Count",
            labels=labels,
            data=data,
            y_label="Number of Recalls",
        ),
    }
