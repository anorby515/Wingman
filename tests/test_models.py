"""Tests for Pydantic data models in backend/models.py."""

import pytest
from pydantic import ValidationError

from backend.models import (
    ArtistConfig,
    ComingSoonPresale,
    ComingSoonShow,
    ConcertState,
    DismissedSuggestion,
    FestivalConfig,
    GeoLocation,
    Show,
    Summary,
    VenueConfig,
    VenueShow,
    WingmanConfig,
)


# ── Show ────────────────────────────────────────────────────────────────────

class TestShow:
    def test_minimal(self):
        s = Show(date="Mar 15, 2026", venue="Kinnick", city="Iowa City, IA")
        assert s.status == "on_sale"
        assert s.lat is None

    def test_with_coords(self):
        s = Show(date="Jun 1, 2026", venue="X", city="Y", lat=41.5, lon=-93.6)
        assert s.lat == 41.5

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            Show(date="X", venue="Y", city="Z", status="invalid")


# ── VenueShow ───────────────────────────────────────────────────────────────

class TestVenueShow:
    def test_basic(self):
        vs = VenueShow(date="Apr 1, 2026", artist="Caamp", tracked=True)
        assert vs.tracked is True


# ── WingmanConfig ───────────────────────────────────────────────────────────

class TestWingmanConfig:
    def test_minimal(self):
        cfg = WingmanConfig(center_city="Des Moines, IA")
        assert cfg.artists == {}
        assert cfg.venues == {}
        assert cfg.festivals == {}
        assert cfg.ticketmaster_api_key is None

    def test_with_artists(self):
        cfg = WingmanConfig(
            center_city="DSM",
            artists={"Caamp": ArtistConfig(url="https://caamp.com")},
        )
        assert "Caamp" in cfg.artists
        assert cfg.artists["Caamp"].genre == "Other"
        assert cfg.artists["Caamp"].paused is False


# ── GeoLocation ─────────────────────────────────────────────────────────────

class TestGeoLocation:
    def test_valid(self):
        g = GeoLocation(lat=41.5, lon=-93.6)
        assert g.lat == 41.5

    def test_out_of_range(self):
        with pytest.raises(ValidationError):
            GeoLocation(lat=100.0, lon=0.0)
        with pytest.raises(ValidationError):
            GeoLocation(lat=0.0, lon=200.0)


# ── ComingSoonShow ──────────────────────────────────────────────────────────

class TestComingSoonShow:
    def test_minimal(self):
        s = ComingSoonShow(
            artist="Zach Bryan",
            date="Aug 15, 2026",
            venue="Wells Fargo Arena",
            city="Des Moines, IA",
            ticketmaster_url="https://ticketmaster.com/event/123",
        )
        assert s.onsale_tbd is False
        assert s.presales == []

    def test_with_presale(self):
        s = ComingSoonShow(
            artist="Tyler Childers",
            date="Sep 1, 2026",
            venue="Kinnick Stadium",
            city="Iowa City, IA",
            ticketmaster_url="https://tm.com/456",
            presales=[
                ComingSoonPresale(name="Fan Club", start_datetime="2026-06-01T10:00:00Z"),
            ],
        )
        assert len(s.presales) == 1


# ── ConcertState ────────────────────────────────────────────────────────────

class TestConcertState:
    def test_minimal(self):
        cs = ConcertState(last_run="2026-02-25", center="Des Moines, IA")
        assert cs.artist_shows == {}

    def test_with_shows(self):
        cs = ConcertState(
            last_run="2026-02-25",
            center="Des Moines, IA",
            artist_shows={
                "Caamp": [Show(date="Jun 1, 2026", venue="X", city="Y")]
            },
        )
        assert len(cs.artist_shows["Caamp"]) == 1


# ── DismissedSuggestion ────────────────────────────────────────────────────

class TestDismissedSuggestion:
    def test_basic(self):
        ds = DismissedSuggestion(
            dismissed_at="2026-02-25",
            resurface_after="2026-08-25",
            source="top_artists_short_term",
        )
        assert ds.reason == "user declined"
