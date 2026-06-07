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

    # Remote: only accept as US if the location explicitly mentions the US.
    # Generic "remote" or "anywhere" without a US marker should NOT be
    # treated as US-only because remote roles may be offered outside the US.
    if lower == "anywhere":
        return False

    if "remote" in lower:
        # Examples that should count as US: "Remote - US", "Remote (United States)",
        # "Remote - USA", "Remote - U.S."
        if "united states" in lower or ", us" in lower or lower.endswith(" us"):
            return True
        if "u.s.a" in lower or "usa" in lower or "u.s." in lower:
            return True
        # Otherwise do not assume remote == US
        return False

    # State abbreviation match (e.g., ", CA" or ", NY").
    # Guard against two-letter ISO country codes returned in the
    # `countryAlpha2Code` field (e.g., "IN" for India) which would
    # otherwise collide with state abbreviations like "IN" (Indiana).
    m = _STATE_ABBREV_RE.search(text)
    if m:
        abbrev = m.group(0).upper()

        # If the matched abbrev appears at the end of the string (typical
        # when Workday emits only the countryAlpha2Code), and there are no
        # other clear US indicators (zip, full state name, major US city),
        # treat it as a country code and only accept if it's explicitly US
        # or a known US territory.
        if re.search(r"[,:\s]" + re.escape(abbrev) + r"\s*$", text):
            if _US_ZIP_RE.search(text) or any(state in lower for state in US_STATES) or any(city in lower for city in MAJOR_US_CITIES):
                return True
            # Accept only explicit US / US-territory codes when trailing
            if abbrev in {"US", "DC", "PR", "GU", "VI"}:
                return True
            return False

        # Otherwise (abbrev appears in-line), accept as a state abbrev
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
