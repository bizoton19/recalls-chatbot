"""
Normalize recall objects for JSON APIs.

CPSC recalls are consumer products only — the DB still has vehicle_* / component
columns for potential future non-CPSC agencies. We omit those keys when unset
so API responses match what the CPSC API actually contains.
"""
from __future__ import annotations

from typing import Any

_VEHICLE_KEYS = ("vehicle_make", "vehicle_model", "vehicle_year_from", "vehicle_year_to", "component")


def prune_empty_vehicle_fields(d: dict[str, Any]) -> dict[str, Any]:
    """Remove vehicle/component keys when all are empty — typical for CPSC-only data."""
    if not any(d.get(k) not in (None, "") for k in _VEHICLE_KEYS):
        for k in _VEHICLE_KEYS:
            d.pop(k, None)
    return d
