"""
CPSC recall client — saferproducts.gov REST API
Docs: https://www.saferproducts.gov/RestWebServices
      https://catalog.data.gov/dataset/cpsc-recalls

Base URL: https://www.saferproducts.gov/RestWebServices/Recall
Format:   ?format=json
Pagination: ?RecallDateStart=YYYY-MM-DD&RecallDateEnd=YYYY-MM-DD
            ?limit=N&offset=N  (not official — use date windows)
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from .base import BaseRecallClient, RecallRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.saferproducts.gov/RestWebServices/Recall"


class CPSCClient(BaseRecallClient):
    agency_code = "CPSC"

    def _parse(self, item: dict) -> RecallRecord:
        recall_date = None
        raw_date = item.get("RecallDate") or item.get("OriginalReleaseDate")
        if raw_date:
            try:
                recall_date = datetime.fromisoformat(raw_date[:10]).date()
            except ValueError:
                pass

        products = item.get("Products") or []
        product = products[0] if products else {}
        brand = product.get("Name", "") or ""
        product_name = product.get("Description", "") or ""
        manufacturer_objs = item.get("Manufacturers") or []
        manufacturer = manufacturer_objs[0].get("Name", "") if manufacturer_objs else None

        hazards = item.get("Hazards") or []
        hazard_text = "; ".join(h.get("Name", "") for h in hazards if h.get("Name")) or None

        remedies = item.get("Remedies") or []
        remedy_text = "; ".join(r.get("Name", "") for r in remedies if r.get("Name")) or None

        recall_id = str(item.get("RecallID", ""))
        recall_number = item.get("RecallNumber") or recall_id

        return RecallRecord(
            agency_code=self.agency_code,
            external_id=recall_id,
            recall_number=recall_number,
            title=item.get("Title") or product_name or "CPSC Recall",
            description=item.get("Description"),
            hazard=hazard_text,
            remedy=remedy_text,
            recall_date=recall_date,
            units_affected=self._parse_units(item.get("ConsumerContact") or ""),
            url=item.get("URL"),
            product_name=product_name or None,
            product_type="Consumer Product",
            brand_name=brand or None,
            manufacturer=manufacturer,
            raw_data=item,
        )

    def _parse_units(self, text: str) -> Optional[int]:
        """Attempt to extract a number from units affected text."""
        import re
        if not text:
            return None
        match = re.search(r"[\d,]+", text.replace(",", ""))
        if match:
            try:
                return int(match.group().replace(",", ""))
            except ValueError:
                pass
        return None

    async def fetch_recent(self, limit: int = 100) -> list[RecallRecord]:
        """Fetch recalls from the last 90 days."""
        end = date.today()
        start = end - timedelta(days=90)
        return await self._fetch_date_range(start, end)

    async def fetch_all(self, page_size: int = 100) -> list[RecallRecord]:
        """
        Full fetch using date-windowed requests.
        CPSC API doesn't have reliable offset pagination, so we slide
        a 180-day window back 10 years.
        """
        results: list[RecallRecord] = []
        end = date.today()
        window_days = 180

        for _ in range(20):  # 20 windows × 180 days = ~10 years
            start = end - timedelta(days=window_days)
            chunk = await self._fetch_date_range(start, end)
            results.extend(chunk)
            logger.info("CPSC: fetched %d recalls for %s–%s", len(chunk), start, end)
            end = start - timedelta(days=1)
            if end.year < 2000:
                break

        return results

    async def _fetch_date_range(self, start: date, end: date) -> list[RecallRecord]:
        params = {
            "format": "json",
            "RecallDateStart": start.isoformat(),
            "RecallDateEnd": end.isoformat(),
        }
        try:
            data = await self._get(BASE_URL, params)
            items = data if isinstance(data, list) else data.get("Recalls", [])
            return [self._parse(item) for item in items]
        except httpx.HTTPStatusError as e:
            logger.error("CPSC API error %s: %s", e.response.status_code, e)
            return []
        except Exception as e:
            logger.error("CPSC fetch error: %s", e)
            return []
