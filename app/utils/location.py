"""US location detection utilities."""

from __future__ import annotations

import re

# All 50 US states + DC + territories
US_STATES: set[str] = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
    "puerto rico", "guam", "u.s. virgin islands",
}

US_STATE_ABBREVIATIONS: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI",
}

# Common US cities that might appear without state
MAJOR_US_CITIES: set[str] = {
    "new york", "los angeles", "chicago", "houston", "phoenix",
    "philadelphia", "san antonio", "san diego", "dallas", "san jose",
    "austin", "jacksonville", "san francisco", "seattle", "denver",
    "boston", "nashville", "baltimore", "portland", "las vegas",
    "atlanta", "miami", "minneapolis", "tampa", "charlotte",
    "raleigh", "pittsburgh", "cincinnati", "st. louis", "orlando",
    "salt lake city", "detroit", "memphis", "louisville",
    "richmond", "sacramento", "tucson", "honolulu", "anchorage",
    "silicon valley", "bay area",
}

# Patterns for US locations
_US_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_STATE_ABBREV_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(s) for s in US_STATE_ABBREVIATIONS) + r")\b"
)


def is_us_location(location_str: str | None) -> bool:
    """Determine whether a location string refers to a US location.

    Handles formats like:
        - "San Francisco, CA"
        - "New York, NY 10001"
        - "Remote - US"
        - "United States"
        - "Austin, Texas"
        - "2 Locations", "3 Locations" (multi-location jobs - accept as US-eligible)
    """
    if not location_str:
        return False

    text = location_str.strip()
    lower = text.lower()

    # Handle multi-location jobs (e.g., "2 Locations", "3 Locations")
    # These are jobs posted at multiple locations; accept them as US-eligible
    # since most companies post US jobs unless explicitly non-US
    if re.match(r'^\d+\s+locations?$', lower):
        return True

    # Explicit country markers
    if "united states" in lower or ", us" in lower or lower.endswith(" us"):
        return True
    if "u.s.a" in lower or "usa" in lower.split():
        return True

    # Exclude obviously non-US
    non_us_markers = [
        "canada", "uk", "united kingdom", "germany", "france", "india",
        "australia", "japan", "china", "singapore", "brazil", "mexico",
        "ireland", "netherlands", "sweden", "switzerland", "spain",
        "italy", "south korea", "israel", "uae", "dubai",
    ]
    if any(m in lower for m in non_us_markers):
        return False

    # Remote - assume US if no non-us markers found (passed previous check)
    if lower == "remote" or lower == "anywhere":
        return True
    
    if "remote" in lower:
        return True

    # State abbreviation match (e.g., ", CA" or ", NY")
    if _STATE_ABBREV_RE.search(text):
        return True

    # Full state name match
    if any(state in lower for state in US_STATES):
        return True

    # Major city match
    if any(city in lower for city in MAJOR_US_CITIES):
        return True

    # US zip code
    if _US_ZIP_RE.search(text):
        return True

    return False
