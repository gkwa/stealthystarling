"""Flatten the harvested reviews JSON into a tidy polars frame."""

import datetime
import json
import logging
import pathlib
import typing

import polars

import reviewquality.dates

logger = logging.getLogger(__name__)


class Harvest(typing.NamedTuple):
    """One harvest file: its metadata plus one row per review."""

    harvested: datetime.date
    source: str
    reviews: polars.DataFrame


def load(path: pathlib.Path) -> Harvest:
    """Read the harvest file and return one row per review."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    harvested_raw = payload.get("harvested")
    if not harvested_raw:
        raise ValueError(f"{path} has no 'harvested' date; cannot estimate review dates")

    harvested = datetime.date.fromisoformat(harvested_raw)
    practices = payload.get("practices") or {}
    if not practices:
        raise ValueError(f"{path} contains no practices")

    rows: list[dict[str, object]] = []
    for key, practice in practices.items():
        for review in practice.get("reviews") or []:
            relative = review.get("date")
            rows.append(
                {
                    "practice": key,
                    "business": practice.get("business") or key,
                    "rating": review.get("rating"),
                    "rating_scale": review.get("rating_scale"),
                    "date_text": relative,
                    "date": reviewquality.dates.estimate_date(relative, harvested),
                    "age_years": reviewquality.dates.age_in_years(relative),
                    "author": review.get("author"),
                    "text_length": len((review.get("text") or "").strip()),
                }
            )

    frame = polars.DataFrame(rows, infer_schema_length=None)
    logger.info("loaded %d reviews across %d practices", frame.height, len(practices))

    unparsed = frame.filter(polars.col("date").is_null()).height
    if unparsed:
        logger.warning("%d reviews had an unparseable relative date", unparsed)

    off_scale = frame.filter(polars.col("rating_scale") != 5).height
    if off_scale:
        logger.warning("%d reviews are not on a 5-point scale", off_scale)

    return Harvest(harvested=harvested, source=payload.get("source") or "", reviews=frame)
