"""
NHTSA recall client — api.nhtsa.gov
Docs: https://api.nhtsa.gov/

Endpoints used:
  GET /recalls/recallsByVehicle?make=&model=&modelYear=   (vehicle-specific)
  GET /products/vehicle/makes                              (all makes)
  GET /recalls/complaintsByVehicle (not used here)

For bulk ingestion we use the NHTSA flat file / dataset feed since the
vehicle-specific endpoint requires make+model+year.

Flat file: https://api.nhtsa.gov/api/complaints/complaintsByVehicle/...
Recalls dataset: https://api.nhtsa.gov/recalls/recallsByVehicle (paginated)

We also use the campaigns feed:
  https://api.nhtsa.gov/recalls/campaignnumber/{campaignNumber}
"""
import logging
from datetime import date, datetime
from typing import Optional

import httpx

from .base import BaseRecallClient, RecallRecord

logger = logging.getLogger(__name__)

CAMPAIGNS_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"
MAKES_URL = "https://api.nhtsa.gov/products/vehicle/makes"


class NHTSAClient(BaseRecallClient):
    agency_code = "NHTSA"

    def _parse(self, item: dict) -> RecallRecord:
        recall_date = None
        raw_date = item.get("reportReceivedDate") or item.get("manufacturerCommunicationDate")
        if raw_date:
            try:
                # NHTSA returns epoch ms sometimes, ISO string otherwise
                if isinstance(raw_date, (int, float)):
                    recall_date = date.fromtimestamp(raw_date / 1000)
                else:
                    recall_date = datetime.fromisoformat(raw_date[:10]).date()
            except (ValueError, OSError):
                pass

        year_str = item.get("modelYear") or ""
        year = None
        if year_str:
            try:
                year = int(year_str)
            except ValueError:
                pass

        campaign = item.get("nhtsaCampaignNumber") or item.get("campaignNumber") or ""

        return RecallRecord(
            agency_code=self.agency_code,
            external_id=campaign or str(item.get("id", "")),
            recall_number=campaign,
            title=item.get("subject") or f"NHTSA Recall {campaign}",
            description=item.get("summary") or item.get("consequence"),
            hazard=item.get("consequence"),
            remedy=item.get("remedy"),
            recall_date=recall_date,
            url=f"https://www.nhtsa.gov/vehicle-safety/recalls?nhtsaId={campaign}" if campaign else None,
            product_type="Vehicle",
            manufacturer=item.get("manufacturer"),
            vehicle_make=item.get("make"),
            vehicle_model=item.get("model"),
            vehicle_year_from=year,
            vehicle_year_to=year,
            component=item.get("component"),
            raw_data=item,
        )

    async def fetch_recent(self, limit: int = 100) -> list[RecallRecord]:
        """Fetch recalls for the most common vehicle makes (top 10) as a proxy for recent."""
        results: list[RecallRecord] = []
        top_makes = ["Toyota", "Ford", "Chevrolet", "Honda", "Nissan", "BMW", "Mercedes-Benz", "Hyundai", "Kia", "Jeep"]
        current_year = date.today().year

        for make in top_makes:
            try:
                data = await self._get(CAMPAIGNS_URL, {
                    "make": make,
                    "model": "All",
                    "modelYear": str(current_year),
                })
                items = data.get("results", []) if isinstance(data, dict) else []
                results.extend(self._parse(item) for item in items)
            except Exception as e:
                logger.warning("NHTSA fetch for %s failed: %s", make, e)

        return results[:limit]

    async def fetch_all(self, page_size: int = 100) -> list[RecallRecord]:
        """
        Full fetch: iterate common makes across years 2000–current.
        For a production system, use the NHTSA flat file download instead.
        """
        results: list[RecallRecord] = []
        makes = await self._fetch_makes()
        current_year = date.today().year

        for make in makes[:50]:  # cap for prototype; remove cap for production
            for year in range(current_year, 2000, -1):
                try:
                    data = await self._get(CAMPAIGNS_URL, {
                        "make": make,
                        "model": "All",
                        "modelYear": str(year),
                    })
                    items = data.get("results", []) if isinstance(data, dict) else []
                    results.extend(self._parse(item) for item in items)
                except httpx.HTTPStatusError:
                    pass
                except Exception as e:
                    logger.warning("NHTSA %s/%s error: %s", make, year, e)

            logger.info("NHTSA: completed make=%s, total=%d", make, len(results))

        return results

    async def _fetch_makes(self) -> list[str]:
        try:
            data = await self._get(MAKES_URL)
            return [m.get("make", "") for m in (data.get("results", []) if isinstance(data, dict) else []) if m.get("make")]
        except Exception as e:
            logger.error("NHTSA makes fetch failed: %s", e)
            return ["Toyota", "Ford", "Chevrolet", "Honda", "Nissan"]
