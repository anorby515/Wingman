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


# ── Venue Show (used by Summary model) ────────────────────────────────────────

class VenueShow(BaseModel):
    """A single event at a tracked venue."""
    date: str = Field(description="Display date")
    artist: str = Field(description="Artist or event name")
    tracked: bool = Field(description="True if artist is in the tracked artists list")


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


class FestivalConfig(BaseModel):
    """Configuration for a single tracked festival."""
    url: str = Field(description="URL to festival lineup/info page")
    paused: bool = Field(default=False, description="If true, not scraped")


class WingmanConfig(BaseModel):
    """Top-level configuration. Written by local UI."""
    center_city: str = Field(description="Map home / default starting position")
    artists: dict[str, ArtistConfig] = Field(default_factory=dict)
    venues: dict[str, VenueConfig] = Field(default_factory=dict)
    festivals: dict[str, FestivalConfig] = Field(default_factory=dict)
    ticketmaster_api_key: Optional[str] = Field(
        default=None,
        description="Ticketmaster Discovery API key for Coming Soon tab",
    )
    spotify_client_id: Optional[str] = Field(
        default=None,
        description="Spotify app Client ID",
    )
    spotify_client_secret: Optional[str] = Field(
        default=None,
        description="Spotify app Client Secret",
    )


# ── Coming Soon (Ticketmaster) ────────────────────────────────────────────────

class ComingSoonPresale(BaseModel):
    """A presale window for an upcoming show."""
    name: str = Field(description="Presale name, e.g. 'Fan Club Presale'")
    start_datetime: Optional[str] = Field(default=None, description="ISO 8601 presale start")
    end_datetime: Optional[str] = Field(default=None, description="ISO 8601 presale end")


class ComingSoonShow(BaseModel):
    """A show not yet on public sale, sourced from Ticketmaster Discovery API."""
    artist: str
    genre: str = "Other"
    date: str = Field(description="Display date, e.g. 'Aug 15, 2026'")
    venue: str
    city: str
    onsale_datetime: Optional[str] = Field(
        default=None,
        description="ISO 8601 public on-sale start (null if TBD)",
    )
    onsale_tbd: bool = Field(default=False, description="True if on-sale date is not yet announced")
    presales: list[ComingSoonPresale] = Field(default_factory=list)
    ticketmaster_url: str = Field(description="Direct link to buy tickets on Ticketmaster")
    lat: Optional[float] = None
    lon: Optional[float] = None


class ComingSoonVenueEvent(BaseModel):
    """A show not yet on public sale at a tracked venue, sourced from Ticketmaster."""
    tracked_venue: str = Field(description="Name of the tracked venue as stored in wingman_config.json")
    artist: str = Field(description="Performing artist or act name")
    date: str = Field(description="Display date, e.g. 'Aug 15, 2026'")
    venue: str = Field(description="TM venue name (may differ slightly from tracked_venue)")
    city: str
    onsale_datetime: Optional[str] = Field(default=None, description="ISO 8601 public on-sale start")
    onsale_tbd: bool = False
    presales: list[ComingSoonPresale] = Field(default_factory=list)
    ticketmaster_url: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class ComingSoonFestivalEvent(BaseModel):
    """A festival event not yet on public sale, sourced from Ticketmaster."""
    tracked_festival: str = Field(description="Festival name as stored in wingman_config.json")
    event_name: str = Field(description="TM event name (may include tier/pass info)")
    date: str = Field(description="Display date, e.g. 'Aug 15, 2026'")
    venue: str
    city: str
    onsale_datetime: Optional[str] = Field(default=None, description="ISO 8601 public on-sale start")
    onsale_tbd: bool = False
    presales: list[ComingSoonPresale] = Field(default_factory=list)
    ticketmaster_url: str
    lat: Optional[float] = None
    lon: Optional[float] = None


# ── Summary (docs/summary.json) ──────────────────────────────────────────────

class SummaryFestivalShow(BaseModel):
    """A festival event in the public summary."""
    date: str
    venue: str
    city: str
    event_name: str = Field(description="TM event name (may differ from tracked festival name)")
    status: Literal["on_sale", "sold_out"] = "on_sale"
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_new: bool = Field(default=False, description="True if added in latest run")


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
    center_lat: float = Field(description="Latitude of center city")
    center_lon: float = Field(description="Longitude of center city")
    artist_shows: dict[str, list[SummaryShow]] = Field(default_factory=dict)
    venue_shows: dict[str, list[VenueShow]] = Field(default_factory=dict)
    festival_shows: dict[str, list[SummaryFestivalShow]] = Field(default_factory=dict)
    festivals_not_found: list[str] = Field(default_factory=list)
    changes: SummaryChanges = Field(default_factory=SummaryChanges)
    coming_soon: list[ComingSoonShow] = Field(
        default_factory=list,
        description="Shows not yet on public sale, sourced from Ticketmaster",
    )
    festival_coming_soon: list[ComingSoonFestivalEvent] = Field(
        default_factory=list,
        description="Festival events not yet on public sale",
    )
    coming_soon_fetched: Optional[str] = Field(
        default=None,
        description="ISO 8601 datetime when coming_soon was last fetched",
    )


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
