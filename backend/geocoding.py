"""
Wingman Geocoding Module
========================
Provides geocoding via OpenStreetMap Nominatim and Haversine distance
calculation. Uses a local JSON cache to avoid repeated API calls.

Usage:
    from backend.geocoding import Geocoder

    geo = Geocoder()
    coords = geo.geocode("Pella, IA")          # -> GeoLocation(lat=41.41, lon=-92.92)
    dist = geo.distance_miles("Pella, IA")       # -> 47.2 (from center city)
    in_range = geo.is_in_range("Pella, IA")      # -> True (if within radius_miles)
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import GeoLocation

# Earth radius in miles
_EARTH_RADIUS_MI = 3958.8

# Nominatim rate limit: 1 request per second
_MIN_REQUEST_INTERVAL = 1.1


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_MI * 2 * math.asin(math.sqrt(a))


class Geocoder:
    """Geocoder with local JSON cache and Nominatim fallback."""

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        center_city: str = "Des Moines, IA",
        radius_miles: float = 200,
    ):
        self.cache_path = cache_path or Path(__file__).parent.parent / "geocode_cache.json"
        self.center_city = center_city
        self.radius_miles = radius_miles
        self._cache: dict[str, GeoLocation] = {}
        self._last_request_time: float = 0
        self._load_cache()
        # Ensure center city is geocoded
        self._center: Optional[GeoLocation] = self.geocode(center_city)

    def _load_cache(self) -> None:
        """Load geocode cache from disk."""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text())
                self._cache = {
                    k: GeoLocation(**v) for k, v in data.items()
                }
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        """Write geocode cache to disk."""
        data = {k: {"lat": v.lat, "lon": v.lon} for k, v in self._cache.items()}
        self.cache_path.write_text(json.dumps(data, indent=2))

    def _nominatim_lookup(self, location: str) -> Optional[GeoLocation]:
        """Query Nominatim API for coordinates. Respects 1 req/sec rate limit."""
        # Rate limit
        elapsed = time.time() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

        encoded = quote(location)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
        req = Request(url, headers={"User-Agent": "Wingman-Concert-Tracker/1.0"})

        try:
            self._last_request_time = time.time()
            with urlopen(req, timeout=10) as resp:
                results = json.loads(resp.read().decode())
            if results:
                return GeoLocation(
                    lat=float(results[0]["lat"]),
                    lon=float(results[0]["lon"]),
                )
        except Exception as e:
            print(f"  Geocoding failed for '{location}': {e}")

        return None

    def geocode(self, location: str) -> Optional[GeoLocation]:
        """Geocode a location string. Returns cached result if available."""
        if not location or not location.strip():
            return None

        location = location.strip()

        # Check cache
        if location in self._cache:
            return self._cache[location]

        # Query Nominatim
        result = self._nominatim_lookup(location)
        if result:
            self._cache[location] = result
            self._save_cache()

        return result

    def distance_miles(self, location: str) -> Optional[float]:
        """Calculate distance in miles from center city to a location."""
        if not self._center:
            return None

        coords = self.geocode(location)
        if not coords:
            return None

        return round(
            haversine(self._center.lat, self._center.lon, coords.lat, coords.lon),
            1,
        )

    def is_in_range(self, location: str) -> bool:
        """Check if a location is within the configured radius."""
        dist = self.distance_miles(location)
        if dist is None:
            return False
        return dist <= self.radius_miles

    def get_center_coords(self) -> Optional[tuple[float, float]]:
        """Return (lat, lon) of the center city, or None if not geocoded."""
        if self._center:
            return (self._center.lat, self._center.lon)
        return None
