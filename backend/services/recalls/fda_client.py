"""
FDA recall client — openFDA API
Docs: https://open.fda.gov/apis/

Endpoints:
  /food/enforcement.json    — food recalls
  /drug/enforcement.json    — drug/medicine recalls
  /device/enforcement.json  — medical device recalls
  /cosmetics/enforcement.json — cosmetics (limited)
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from .base import BaseRecallClient, RecallRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://api.fda.gov"
ENDPOINTS = {
    "food":      f"{BASE_URL}/food/enforcement.json",
    "drug":      f"{BASE_URL}/drug/enforcement.json",
    "device":    f"{BASE_URL}/device/enforcement.json",
}


class FDAClient(BaseRecallClient):
    agency_code = "FDA"

    def _parse(self, item: dict, product_type: str) -> RecallRecord:
        recall_date = None
        raw_date = item.get("recall_initiation_date") or item.get("report_date")
        if raw_date:
            try:
                recall_date = datetime.strptime(raw_date, "%Y%m%d").date()
            except ValueError:
                try:
                    recall_date = datetime.fromisoformat(raw_date[:10]).date()
                except ValueError:
                    pass

        event_id = str(item.get("event_id", ""))
        recall_number = item.get("recall_number") or event_id

        type_labels = {
            "food": "Food/Beverage",
            "drug": "Drug/Medicine",
            "device": "Medical Device",
        }

        return RecallRecord(
            agency_code=self.agency_code,
            external_id=f"{product_type}_{event_id}" if event_id else recall_number,
            recall_number=recall_number,
            title=item.get("reason_for_recall") or f"FDA {type_labels.get(product_type, 'Product')} Recall",
            description=item.get("product_description"),
            hazard=item.get("code_info"),
            remedy=None,
            recall_date=recall_date,
            url=None,
            product_name=item.get("product_description"),
            product_type=type_labels.get(product_type, "FDA Product"),
            brand_name=item.get("brand_name"),
            manufacturer=item.get("recalling_firm"),
            product_quantity=item.get("product_quantity"),
            distribution_pattern=item.get("distribution_pattern"),
            reason_for_recall=item.get("reason_for_recall"),
            classification=item.get("classification"),  # Class I, II, III
            raw_data=item,
        )

    async def _fetch_endpoint(self, endpoint_key: str, params: dict) -> list[RecallRecord]:
        url = ENDPOINTS[endpoint_key]
        try:
            data = await self._get(url, params)
            results = data.get("results", []) if isinstance(data, dict) else []
            return [self._parse(r, endpoint_key) for r in results]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # No results for this query window
            logger.error("FDA %s API error %s: %s", endpoint_key, e.response.status_code, e)
            return []
        except Exception as e:
            logger.error("FDA %s fetch error: %s", endpoint_key, e)
            return []

    async def fetch_recent(self, limit: int = 100) -> list[RecallRecord]:
        end = date.today()
        start = end - timedelta(days=90)
        date_filter = f"recall_initiation_date:[{start.strftime('%Y%m%d')}+TO+{end.strftime('%Y%m%d')}]"

        results: list[RecallRecord] = []
        for ep in ENDPOINTS:
            chunk = await self._fetch_endpoint(ep, {
                "search": date_filter,
                "limit": min(limit, 100),
            })
            results.extend(chunk)

        return results

    async def fetch_all(self, page_size: int = 100) -> list[RecallRecord]:
        results: list[RecallRecord] = []

        for ep in ENDPOINTS:
            skip = 0
            while True:
                chunk = await self._fetch_endpoint(ep, {
                    "limit": page_size,
                    "skip": skip,
                })
                if not chunk:
                    break
                results.extend(chunk)
                logger.info("FDA %s: fetched %d (offset %d)", ep, len(chunk), skip)
                skip += page_size
                if len(chunk) < page_size:
                    break
                if skip >= 25000:
                    # openFDA hard caps at 25,000 records per endpoint
                    logger.info("FDA %s: reached openFDA 25k cap", ep)
                    break

        return results
