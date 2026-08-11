"""Convert Google's relative review dates into estimated calendar dates.

Google buckets ages coarsely: anything from 12 to 23 months reads as "a year
ago". An estimate derived from a bucket therefore carries roughly half the
bucket width as error, which is about six months for the year-granularity
entries. Treat the output as an approximate date, not a precise one.
"""

import datetime
import re
import typing

DAYS_PER_UNIT: typing.Final[dict[str, float]] = {
    "hour": 1.0 / 24.0,
    "day": 1.0,
    "week": 7.0,
    "month": 30.44,
    "year": 365.25,
}

_EDITED = re.compile(r"^edited\s+", re.IGNORECASE)
_RELATIVE = re.compile(
    r"^(?P<count>a|an|\d+)\s+(?P<unit>hour|day|week|month|year)s?\s+ago$",
    re.IGNORECASE,
)


def age_in_days(relative: str | None) -> float | None:
    """Return the age a relative date string encodes, or None if unparseable."""
    if not relative:
        return None

    text = _EDITED.sub("", relative.strip()).lower()
    match = _RELATIVE.match(text)
    if match is None:
        return None

    raw_count = match.group("count")
    count = 1.0 if raw_count in ("a", "an") else float(raw_count)
    return count * DAYS_PER_UNIT[match.group("unit")]


def estimate_date(relative: str | None, harvested: datetime.date) -> datetime.date | None:
    """Return the estimated calendar date of a review, or None if unparseable."""
    days = age_in_days(relative)
    if days is None:
        return None

    return harvested - datetime.timedelta(days=round(days))


def age_in_years(relative: str | None) -> float | None:
    """Return the age in years a relative date string encodes."""
    days = age_in_days(relative)
    if days is None:
        return None

    return days / 365.25
