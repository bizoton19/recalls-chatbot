"""
CPSC recall client — saferproducts.gov REST API
Docs: https://www.saferproducts.gov/RestWebServices
      https://catalog.data.gov/dataset/cpsc-recalls

Base URL: https://www.saferproducts.gov/RestWebServices/Recall
Format:   ?format=json
Pagination: ?RecallDateStart=YYYY-MM-DD&RecallDateEnd=YYYY-MM-DD
            ?limit=N&offset=N  (not official — use date windows)

Importer maps every top-level and nested field from the API JSON into:
  - typed columns on Recall (searchable / embeddable)
  - raw_data: full API payload preserved verbatim for forward compatibility
"""
import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from .base import BaseRecallClient, RecallRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.saferproducts.gov/RestWebServices/Recall"


def _parse_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val[:10]).date()
    except ValueError:
        return None


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


class CPSCClient(BaseRecallClient):
    agency_code = "CPSC"

    def _parse(self, item: dict) -> RecallRecord:
        recall_date = _parse_date(item.get("RecallDate") or item.get("OriginalReleaseDate"))
        last_publish_date = _parse_date(item.get("LastPublishDate"))

        products = item.get("Products") or []

        product_names = _dedupe_preserve([p.get("Name") or "" for p in products if p.get("Name")])
        brand_name = product_names[0] if product_names else None
        product_name = " | ".join(product_names) if len(product_names) > 1 else (product_names[0] if product_names else None)

        desc_parts = [p.get("Description") for p in products if p.get("Description")]
        product_description = " | ".join(desc_parts) if desc_parts else None

        model_numbers: list[str] = []
        for p in products:
            m = (p.get("Model") or "").strip()
            if m:
                model_numbers.append(m)

        type_vals = [p.get("Type") for p in products if p.get("Type")]
        product_type = type_vals[0] if type_vals else "Consumer Product"

        units_affected: Optional[int] = None
        for p in products:
            u = self._parse_units(p.get("NumberOfUnits") or "")
            if u is not None:
                units_affected = u
                break
        if units_affected is None:
            units_affected = self._parse_units(item.get("ConsumerContact") or "")

        manufacturers = item.get("Manufacturers") or []
        mfr_names = [m.get("Name") for m in manufacturers if m.get("Name")]
        manufacturer = "; ".join(mfr_names) if mfr_names else None

        manufacturer_countries: list[str] = []
        for mc in item.get("ManufacturerCountries") or []:
            c = (mc.get("Country") or "").strip()
            if c:
                manufacturer_countries.append(c)
        manufacturer_countries = _dedupe_preserve(manufacturer_countries)

        hazards = item.get("Hazards") or []
        hazard_text = "; ".join(h.get("Name", "") for h in hazards if h.get("Name")) or None

        remedies = item.get("Remedies") or []
        remedy_text = "; ".join(r.get("Name", "") for r in remedies if r.get("Name")) or None

        retailers = item.get("Retailers") or []
        ret_text = "; ".join(r.get("Name") for r in retailers if r.get("Name"))
        distributors = item.get("Distributors") or []
        dist_text = "; ".join(d.get("Name") for d in distributors if d.get("Name"))
        importers = item.get("Importers") or []
        imp_text = "; ".join(i.get("Name") for i in importers if i.get("Name"))
        dist_parts = [p for p in [ret_text, dist_text, imp_text] if p]
        distribution_pattern = " | ".join(dist_parts) if dist_parts else None

        injuries = item.get("Injuries") or []
        injury_text = "; ".join(i.get("Name") for i in injuries if i.get("Name")) or None

        recall_id = str(item.get("RecallID", ""))
        recall_number = item.get("RecallNumber") or recall_id

        title = item.get("Title") or product_name or "CPSC Recall"

        product_quantity = item.get("ConsumerContact")

        return RecallRecord(
            agency_code=self.agency_code,
            external_id=recall_id,
            recall_number=recall_number,
            title=title,
            description=item.get("Description"),
            hazard=hazard_text,
            remedy=remedy_text,
            recall_date=recall_date,
            units_affected=units_affected,
            url=item.get("URL"),
            product_name=product_name,
            product_description=product_description,
            product_type=product_type,
            brand_name=brand_name,
            manufacturer=manufacturer,
            model_numbers=model_numbers,
            vehicle_make=None,
            vehicle_model=None,
            vehicle_year_from=None,
            vehicle_year_to=None,
            component=None,
            product_quantity=product_quantity,
            distribution_pattern=distribution_pattern,
            reason_for_recall=injury_text,
            classification=None,
            manufacturer_countries=manufacturer_countries,
            last_publish_date=last_publish_date,
            raw_data=item,
        )

    def _parse_units(self, text: str) -> Optional[int]:
        """Extract a numeric unit count from CPSC text (e.g. 'About 640')."""
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
