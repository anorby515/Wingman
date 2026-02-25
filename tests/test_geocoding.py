"""Tests for backend/geocoding.py module."""

import json
import math
from pathlib import Path
from unittest.mock import patch

from backend.geocoding import Geocoder, haversine
from backend.models import GeoLocation


class TestHaversine:
    def test_same_point(self):
        assert haversine(41.5, -93.6, 41.5, -93.6) == 0.0

    def test_known_distance(self):
        # Des Moines to Chicago is ~310 miles
        dist = haversine(41.5868, -93.625, 41.8781, -87.6298)
        assert 300 < dist < 320

    def test_symmetry(self):
        d1 = haversine(41.5, -93.6, 40.0, -89.0)
        d2 = haversine(40.0, -89.0, 41.5, -93.6)
        assert math.isclose(d1, d2, rel_tol=1e-9)


class TestGeocoder:
    def test_loads_from_cache(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
            "Chicago, IL": {"lat": 41.8781, "lon": -87.6298},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")
            result = geo.geocode("Chicago, IL")
            assert result is not None
            assert result.lat == 41.8781

    def test_cache_hit_no_network(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None) as mock_nom:
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")
            result = geo.geocode("Des Moines, IA")
            assert result is not None
            # Nominatim should NOT have been called for the second lookup
            # (it's called once for center city init, but that also hits cache)
            # The center_city lookup in __init__ hits cache, so no network calls
            mock_nom.assert_not_called()

    def test_distance_miles(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
            "Iowa City, IA": {"lat": 41.6611, "lon": -91.5302},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")
            dist = geo.distance_miles("Iowa City, IA")
            assert dist is not None
            assert 100 < dist < 130  # ~112 miles

    def test_is_in_range(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
            "Iowa City, IA": {"lat": 41.6611, "lon": -91.5302},
            "Denver, CO": {"lat": 39.7392, "lon": -104.9903},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA", radius_miles=200)
            assert geo.is_in_range("Iowa City, IA") is True
            assert geo.is_in_range("Denver, CO") is False

    def test_geocode_empty_string(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")
            assert geo.geocode("") is None
            assert geo.geocode("   ") is None

    def test_get_center_coords(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
        }))

        with patch.object(Geocoder, "_nominatim_lookup", return_value=None):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")
            coords = geo.get_center_coords()
            assert coords == (41.5868, -93.625)

    def test_saves_to_cache(self, tmp_path: Path):
        cache_file = tmp_path / "geocode_cache.json"
        cache_file.write_text(json.dumps({
            "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
        }))

        new_loc = GeoLocation(lat=40.0, lon=-90.0)
        with patch.object(Geocoder, "_nominatim_lookup", return_value=new_loc):
            geo = Geocoder(cache_path=cache_file, center_city="Des Moines, IA")

        # Now look up something not in cache, but mock nominatim to return a result
        with patch.object(Geocoder, "_nominatim_lookup", return_value=GeoLocation(lat=39.0, lon=-94.0)):
            result = geo.geocode("Kansas City, MO")
            assert result is not None
            assert result.lat == 39.0

        # Verify cache file was updated
        saved = json.loads(cache_file.read_text())
        assert "Kansas City, MO" in saved
