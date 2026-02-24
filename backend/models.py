"""
Wingman Data Models
===================
Pydantic models that define the contract for all shared data files.
Both the backend API and the validation script use these models.

These models are the code-level equivalent of the JSON schemas in schemas/.
If you change a model here, update the corresponding schema file too.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Concert State (concert_state.json) ────────────────────────────────────────

class Show(BaseModel):
    """A single artist show (North America scope)."""
    date: str = Field(description="Display date, e.g. 'Mar 15, 2026'")
    venue: str = Field(description="Venue name")
    city: str = Field(description="City and state, e.g. 'Kansas City, MO'")
    status: Literal["on_sale", "sold_out"] = "on_sale"
    lat: Optional[float] = Field(default=None, description="Venue latitude")
    lon: Optional[float] = Field(default=None, description="Venue longitude")


class VenueShow(BaseModel):
    """A single event at a tracked venue."""
    date: str = Field(description="Display date")
    artist: str = Field(description="Artist or event name")
    tracked: bool = Field(description="True if artist is in the tracked artists list")


class ConcertState(BaseModel):
    """Top-level concert state. Written by Cowork after each scrape run."""
    last_run: str = Field(description="Date of last run, YYYY-MM-DD")
    center: str = Field(description="Map home city, e.g. 'Des Moines, IA'")
    radius_miles: Optional[float] = Field(
        default=None,
        description="Deprecated — kept for backward compat, no longer used for filtering",
    )
    artist_shows: dict[str, list[Show]] = Field(
        default_factory=dict,
        description="Map of artist name to all North America shows",
    )
    venue_shows: dict[str, list[VenueShow]] = Field(
        default_factory=dict,
        description="Map of venue name to events at that venue",
    )


# ── Wingman Config (wingman_config.json) ──────────────────────────────────────

class ArtistConfig(BaseModel):
    """Configuration for a single tracked artist."""
    url: str = Field(description="URL to artist's tour/shows page")
    genre: str = Field(default="Other", description="Genre category")
    paused: bool = Field(default=False, description="If true, not scraped")


class VenueConfig(BaseModel):
    """Configuration for a single tracked venue."""
    url: str = Field(description="URL to venue's events/calendar page")
    city: str = Field(description="Venue city, e.g. 'Des Moines, IA'")
    is_local: bool = Field(default=False, description="True if local venue")
    paused: bool = Field(default=False, description="If true, not scraped")


class WingmanConfig(BaseModel):
    """Top-level configuration. Written by local UI, read by Cowork."""
    center_city: str = Field(description="Map home / default starting position")
    radius_miles: Optional[float] = Field(
        default=None,
        description="Deprecated — kept for backward compat",
    )
    cities_in_range: list[str] = Field(
        default_factory=list,
        description="Deprecated — kept for backward compat",
    )
    states_in_range: list[str] = Field(
        default_factory=list,
        description="Deprecated — kept for backward compat",
    )
    artists: dict[str, ArtistConfig] = Field(default_factory=dict)
    venues: dict[str, VenueConfig] = Field(default_factory=dict)


# ── Summary (docs/summary.json) ──────────────────────────────────────────────

class SummaryShow(BaseModel):
    """A show in the public summary, with optional 'new this week' flag."""
    date: str
    venue: str
    city: str
    status: Literal["on_sale", "sold_out"] = "on_sale"
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_new: bool = Field(default=False, description="True if added in latest run")


class ArtistChanges(BaseModel):
    """Changes for a single artist between runs."""
    added: list[SummaryShow] = Field(default_factory=list)
    removed: list[SummaryShow] = Field(default_factory=list)
    newly_sold: list[SummaryShow] = Field(default_factory=list)


class VenueChanges(BaseModel):
    """Changes for a single venue between runs."""
    added: list[VenueShow] = Field(default_factory=list)
    removed: list[VenueShow] = Field(default_factory=list)


class SummaryChanges(BaseModel):
    """All changes from the latest run."""
    artists: dict[str, ArtistChanges] = Field(default_factory=dict)
    venues: dict[str, VenueChanges] = Field(default_factory=dict)
    total_added: int = 0
    total_removed: int = 0
    total_sold_out: int = 0


class Summary(BaseModel):
    """Public summary for GitHub Pages."""
    generated_at: str = Field(description="YYYY-MM-DD")
    center: str
    radius_miles: Optional[float] = Field(
        default=None,
        description="Deprecated — kept for backward compat",
    )
    center_lat: float = Field(description="Latitude of center city")
    center_lon: float = Field(description="Longitude of center city")
    artist_shows: dict[str, list[SummaryShow]] = Field(default_factory=dict)
    venue_shows: dict[str, list[VenueShow]] = Field(default_factory=dict)
    changes: SummaryChanges = Field(default_factory=SummaryChanges)


# ── Geocode Cache (geocode_cache.json) ────────────────────────────────────────

class GeoLocation(BaseModel):
    """A cached geocoding result."""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


# ── Dismissed Suggestions (dismissed_suggestions.json) ────────────────────────

class DismissedSuggestion(BaseModel):
    """A Spotify artist suggestion that was dismissed by the user."""
    dismissed_at: str = Field(description="YYYY-MM-DD")
    resurface_after: str = Field(description="YYYY-MM-DD (6 months from dismissal)")
    reason: str = Field(default="user declined")
    source: str = Field(
        description="Where suggestion came from, e.g. 'top_artists_medium_term'"
    )
