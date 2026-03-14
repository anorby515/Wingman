"""Tests for models not covered by existing test_models.py."""

import pytest
from pydantic import ValidationError

from backend.models import (
    ArtistChanges,
    ComingSoonFestivalEvent,
    ComingSoonPresale,
    ComingSoonVenueEvent,
    Summary,
    SummaryChanges,
    SummaryFestivalShow,
    SummaryShow,
    VenueChanges,
    VenueShow,
)


# ── ComingSoonVenueEvent ─────────────────────────────────────────────────────

class TestComingSoonVenueEvent:
    def test_all_fields(self):
        e = ComingSoonVenueEvent(
            tracked_venue="Wells Fargo Arena",
            artist="Zach Bryan",
            date="Jun 20, 2026",
            venue="Wells Fargo Arena",
            city="Des Moines, IA",
            onsale_datetime="2026-03-15T10:00:00Z",
            onsale_tbd=False,
            presales=[ComingSoonPresale(name="Fan Club", start_datetime="2026-03-14T10:00:00Z")],
            ticketmaster_url="https://tm.com/123",
            lat=41.59,
            lon=-93.62,
        )
        assert e.tracked_venue == "Wells Fargo Arena"
        assert e.lat == 41.59
        assert len(e.presales) == 1

    def test_optional_fields(self):
        e = ComingSoonVenueEvent(
            tracked_venue="Wells Fargo Arena",
            artist="Zach Bryan",
            date="Jun 20, 2026",
            venue="Wells Fargo Arena",
            city="Des Moines, IA",
            ticketmaster_url="https://tm.com/123",
        )
        assert e.onsale_datetime is None
        assert e.onsale_tbd is False
        assert e.presales == []
        assert e.lat is None
        assert e.lon is None


# ── ComingSoonFestivalEvent ──────────────────────────────────────────────────

class TestComingSoonFestivalEvent:
    def test_all_fields(self):
        e = ComingSoonFestivalEvent(
            tracked_festival="Hinterland",
            event_name="Hinterland Music Festival 2026",
            date="Aug 1, 2026",
            venue="Avenue of the Saints",
            city="St. Charles, IA",
            onsale_datetime="2026-04-01T10:00:00Z",
            onsale_tbd=False,
            presales=[],
            ticketmaster_url="https://tm.com/456",
            lat=41.29,
            lon=-93.07,
        )
        assert e.tracked_festival == "Hinterland"
        assert e.event_name == "Hinterland Music Festival 2026"

    def test_optional_fields(self):
        e = ComingSoonFestivalEvent(
            tracked_festival="Hinterland",
            event_name="Hinterland 2026",
            date="Aug 1, 2026",
            venue="Avenue of the Saints",
            city="St. Charles, IA",
            ticketmaster_url="https://tm.com/456",
        )
        assert e.onsale_datetime is None
        assert e.lat is None


# ── Summary ──────────────────────────────────────────────────────────────────

class TestSummary:
    def test_full_model_with_nested(self):
        s = Summary(
            generated_at="2026-03-14",
            center="Des Moines, IA",
            center_lat=41.5868,
            center_lon=-93.625,
            artist_shows={
                "Caamp": [SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI")]
            },
            venue_shows={
                "Wells Fargo Arena": [VenueShow(date="Jun 20, 2026", artist="Zach Bryan", tracked=True)]
            },
            festival_shows={
                "Hinterland": [SummaryFestivalShow(
                    date="Aug 1, 2026", venue="Avenue", city="St. Charles, IA",
                    event_name="Hinterland Music Festival",
                )]
            },
            festivals_not_found=["FakeFest"],
            changes=SummaryChanges(total_added=2, total_removed=0, total_sold_out=1),
            coming_soon=[],
            festival_coming_soon=[],
        )
        assert s.generated_at == "2026-03-14"
        assert len(s.artist_shows["Caamp"]) == 1
        assert s.changes.total_added == 2
        assert s.festivals_not_found == ["FakeFest"]

    def test_minimal(self):
        s = Summary(
            generated_at="2026-03-14",
            center="Des Moines, IA",
            center_lat=41.5868,
            center_lon=-93.625,
        )
        assert s.artist_shows == {}
        assert s.venue_shows == {}
        assert s.festival_shows == {}
        assert s.coming_soon == []
        assert s.coming_soon_fetched is None


# ── SummaryShow ──────────────────────────────────────────────────────────────

class TestSummaryShow:
    def test_on_sale_status(self):
        s = SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI", status="on_sale")
        assert s.status == "on_sale"

    def test_sold_out_status(self):
        s = SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI", status="sold_out")
        assert s.status == "sold_out"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI", status="cancelled")

    def test_default_status(self):
        s = SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI")
        assert s.status == "on_sale"
        assert s.is_new is False
        assert s.lat is None


# ── SummaryFestivalShow ──────────────────────────────────────────────────────

class TestSummaryFestivalShow:
    def test_all_fields(self):
        s = SummaryFestivalShow(
            date="Aug 1, 2026",
            venue="Avenue of the Saints",
            city="St. Charles, IA",
            event_name="Hinterland Music Festival",
            status="on_sale",
            lat=41.29,
            lon=-93.07,
            is_new=True,
        )
        assert s.event_name == "Hinterland Music Festival"
        assert s.is_new is True
        assert s.lat == 41.29

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            SummaryFestivalShow(
                date="Aug 1, 2026", venue="V", city="C",
                event_name="E", status="pending",
            )


# ── ArtistChanges ────────────────────────────────────────────────────────────

class TestArtistChanges:
    def test_defaults(self):
        ac = ArtistChanges()
        assert ac.added == []
        assert ac.removed == []
        assert ac.newly_sold == []

    def test_populated(self):
        show = SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI")
        ac = ArtistChanges(added=[show], removed=[], newly_sold=[show])
        assert len(ac.added) == 1
        assert len(ac.newly_sold) == 1


# ── VenueChanges ─────────────────────────────────────────────────────────────

class TestVenueChanges:
    def test_defaults(self):
        vc = VenueChanges()
        assert vc.added == []
        assert vc.removed == []

    def test_populated(self):
        show = VenueShow(date="Jun 20, 2026", artist="Zach Bryan", tracked=True)
        vc = VenueChanges(added=[show])
        assert len(vc.added) == 1


# ── SummaryChanges ───────────────────────────────────────────────────────────

class TestSummaryChanges:
    def test_defaults(self):
        sc = SummaryChanges()
        assert sc.artists == {}
        assert sc.venues == {}
        assert sc.total_added == 0
        assert sc.total_removed == 0
        assert sc.total_sold_out == 0

    def test_populated(self):
        show = SummaryShow(date="Jun 1, 2026", venue="Sylvee", city="Madison, WI")
        sc = SummaryChanges(
            artists={"Caamp": ArtistChanges(added=[show])},
            venues={},
            total_added=1,
            total_removed=0,
            total_sold_out=0,
        )
        assert len(sc.artists["Caamp"].added) == 1
        assert sc.total_added == 1
