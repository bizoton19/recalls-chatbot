from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@dataclass
class RecallRecord:
    """Normalized recall record, agency-agnostic."""
    agency_code: str
    external_id: str
    title: str

    description: Optional[str] = None
    hazard: Optional[str] = None
    remedy: Optional[str] = None
    recall_date: Optional[date] = None
    recall_number: Optional[str] = None
    units_affected: Optional[int] = None
    url: Optional[str] = None

    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_type: Optional[str] = None
    brand_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model_numbers: list[str] = field(default_factory=list)

    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year_from: Optional[int] = None
    vehicle_year_to: Optional[int] = None
    component: Optional[str] = None

    product_quantity: Optional[str] = None
    distribution_pattern: Optional[str] = None
    reason_for_recall: Optional[str] = None
    classification: Optional[str] = None

    raw_data: Optional[dict] = None


class BaseRecallClient(ABC):
    """Abstract base for all federal recall API clients."""

    agency_code: str

    @abstractmethod
    async def fetch_recent(self, limit: int = 100) -> list[RecallRecord]:
        """Fetch the most recent recalls."""

    @abstractmethod
    async def fetch_all(self, page_size: int = 100) -> list[RecallRecord]:
        """Fetch all available recalls (for full re-index)."""

    async def _get(self, url: str, params: dict = None) -> dict | list:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params or {})
            resp.raise_for_status()
            return resp.json()
