"""
USDA/FSIS recall client
Docs: https://www.fsis.usda.gov/recalls

API: https://www.fsis.usda.gov/fsis/api/recall/v/1
Returns JSON list of meat, poultry, and egg product recalls.
"""
import logging
from datetime import date, datetime

import httpx

from .base import BaseRecallClient, RecallRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fsis.usda.gov/fsis/api/recall/v/1"


class USDAClient(BaseRecallClient):
    agency_code = "USDA"

    def _parse(self, item: dict) -> RecallRecord:
        recall_date = None
        raw_date = item.get("field_recall_date") or item.get("created")
        if raw_date:
            try:
                recall_date = datetime.fromisoformat(raw_date[:10]).date()
            except ValueError:
                pass

        recall_id = str(item.get("nid") or item.get("id") or "")
        title = item.get("title") or item.get("field_title") or "USDA/FSIS Recall"

        return RecallRecord(
            agency_code=self.agency_code,
            external_id=recall_id,
            recall_number=item.get("field_recall_number"),
            title=title,
            description=item.get("body") or item.get("field_summary"),
            hazard=item.get("field_health_risk_text"),
            remedy=None,
            recall_date=recall_date,
            url=f"https://www.fsis.usda.gov/recalls/{recall_id}" if recall_id else None,
            product_name=item.get("field_product_items"),
            product_type="Meat/Poultry/Egg",
            brand_name=item.get("field_establishment"),
            manufacturer=item.get("field_establishment"),
            product_quantity=item.get("field_quantity"),
            distribution_pattern=item.get("field_states_affected"),
            reason_for_recall=item.get("field_reason"),
            classification=item.get("field_recall_class"),
            raw_data=item,
        )

    async def fetch_recent(self, limit: int = 100) -> list[RecallRecord]:
        try:
            data = await self._get(BASE_URL, {"_format": "json", "page[limit]": limit})
            items = data if isinstance(data, list) else data.get("data", [])
            return [self._parse(item) for item in items[:limit]]
        except httpx.HTTPStatusError as e:
            logger.error("USDA API error %s: %s", e.response.status_code, e)
            return []
        except Exception as e:
            logger.error("USDA fetch error: %s", e)
            return []

    async def fetch_all(self, page_size: int = 100) -> list[RecallRecord]:
        results: list[RecallRecord] = []
        page = 0

        while True:
            try:
                data = await self._get(BASE_URL, {
                    "_format": "json",
                    "page[limit]": page_size,
                    "page[offset]": page * page_size,
                })
                items = data if isinstance(data, list) else data.get("data", [])
                if not items:
                    break
                results.extend(self._parse(item) for item in items)
                logger.info("USDA: page %d, total=%d", page, len(results))
                page += 1
                if len(items) < page_size:
                    break
            except Exception as e:
                logger.error("USDA page %d error: %s", page, e)
                break

        return results
