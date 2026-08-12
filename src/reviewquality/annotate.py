"""Add an approximate calendar date to every review in a harvest file.

Google states review ages relatively, so the approximation is the harvest date
minus the stated offset. See reviewquality.dates for the error that carries.
"""

import datetime
import json
import logging
import pathlib
import typing

import reviewquality.dates

logger = logging.getLogger(__name__)

FIELD: typing.Final[str] = "date_approx"
ANCHOR: typing.Final[str] = "date"


class Counts(typing.NamedTuple):
    """How many reviews an annotation pass dated and how many it could not."""

    dated: int
    undated: int


def _with_date(review: dict[str, object], harvested: datetime.date) -> dict[str, object]:
    """Return the review with FIELD inserted immediately after its relative date."""
    relative = review.get(ANCHOR)
    estimate = reviewquality.dates.estimate_date(
        relative if isinstance(relative, str) else None, harvested
    )
    value = estimate.isoformat() if estimate else None

    annotated: dict[str, object] = {}
    for key, existing in review.items():
        if key == FIELD:
            continue
        annotated[key] = existing
        if key == ANCHOR:
            annotated[FIELD] = value

    if FIELD not in annotated:
        annotated[FIELD] = value

    return annotated


def annotate(payload: dict[str, typing.Any]) -> Counts:
    """Rewrite the payload's reviews in place, adding an approximate date to each."""
    harvested_raw = payload.get("harvested")
    if not harvested_raw:
        raise ValueError("harvest file has no 'harvested' date; cannot estimate review dates")

    harvested = datetime.date.fromisoformat(harvested_raw)
    practices = payload.get("practices") or {}
    if not practices:
        raise ValueError("harvest file contains no practices")

    dated = 0
    undated = 0
    for practice in practices.values():
        annotated = [_with_date(review, harvested) for review in practice.get("reviews") or []]
        for review in annotated:
            if review[FIELD] is None:
                undated += 1
            else:
                dated += 1
        if annotated:
            practice["reviews"] = annotated

    logger.info("dated %d reviews across %d practices", dated, len(practices))
    if undated:
        logger.warning("%d reviews had an unparseable relative date", undated)

    return Counts(dated=dated, undated=undated)


def annotate_file(source: pathlib.Path, destination: pathlib.Path) -> Counts:
    """Read a harvest file, annotate every review, and write the result out."""
    payload = json.loads(source.read_text(encoding="utf-8"))
    counts = annotate(payload)
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return counts
