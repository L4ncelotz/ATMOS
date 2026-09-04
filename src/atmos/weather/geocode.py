"""Open-Meteo geocoding: free-text "city name" → Location.

Endpoint: https://geocoding-api.open-meteo.com/v1/search
No API key. Returns top N results; we keep the first by relevance score.

If the query fails or returns no results, raises ValueError. Cache layer
does not apply here — geocoding is cheap and we want fresh results.
"""

from __future__ import annotations

import httpx

from atmos.weather.location import Location

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT_S = 8.0


def resolve_location(query: str, count: int = 5) -> list[Location]:
    """Return up to `count` matches for `query`, ranked by Open-Meteo relevance."""
    if not query.strip():
        raise ValueError("empty location query")
    resp = httpx.get(
        GEOCODE_URL,
        params={"name": query, "count": count, "language": "en", "format": "json"},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    payload = resp.json()
    results = payload.get("results") or []
    out: list[Location] = []
    for r in results:
        try:
            out.append(
                Location(
                    name=str(r["name"]),
                    country=str(r.get("country", "")),
                    latitude=float(r["latitude"]),
                    longitude=float(r["longitude"]),
                    timezone=str(r.get("timezone", "UTC")),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def first_location(query: str) -> Location:
    """Convenience: resolve and return the top match, or raise."""
    matches = resolve_location(query, count=1)
    if not matches:
        raise ValueError(f"no location found for {query!r}")
    return matches[0]