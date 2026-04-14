"""
Shared WHERE clauses for structured recall filters (advanced search + LLM tools).
"""
from datetime import date
from typing import Optional

from sqlalchemy import Select, or_, text

from models.recall import Recall


def apply_recall_filters(
    stmt: Select,
    *,
    agency_code: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    brand: Optional[str] = None,
    product_type: Optional[str] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
) -> Select:
    """Apply filters to a SELECT that already targets `recalls` (any FROM shape)."""
    if agency_code:
        stmt = stmt.where(Recall.agency_code == agency_code.strip().upper())
    if date_from:
        stmt = stmt.where(Recall.recall_date >= date_from)
    if date_to:
        stmt = stmt.where(Recall.recall_date <= date_to)
    if brand:
        stmt = stmt.where(Recall.brand_name.ilike(f"%{brand.strip()}%"))
    if product_type:
        stmt = stmt.where(Recall.product_type.ilike(f"%{product_type.strip()}%"))
    if country:
        c = country.strip()
        stmt = stmt.where(
            text(
                "("
                "EXISTS (SELECT 1 FROM unnest(COALESCE(manufacturer_countries, ARRAY[]::text[])) AS x "
                " WHERE lower(x) LIKE lower(:c_like))"
                " OR EXISTS (SELECT 1 FROM jsonb_array_elements("
                " COALESCE(raw_data->'ManufacturerCountries', '[]'::jsonb)) elem "
                " WHERE lower(trim(elem->>'Country')) LIKE lower(:c_like))"
                ")"
            ).bindparams(c_like=f"%{c}%")
        )
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Recall.title.ilike(term),
                Recall.description.ilike(term),
                Recall.hazard.ilike(term),
                Recall.product_name.ilike(term),
                Recall.manufacturer.ilike(term),
            )
        )
    return stmt
