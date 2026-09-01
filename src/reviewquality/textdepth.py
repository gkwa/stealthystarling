"""Measure how much a practice's reviewers actually wrote, not how they scored.

Every column in the scored table comes from the star alone, so a practice with
hundreds of bare five-star ratings and one with hundreds of paragraphs look
identical there. This pass reads the text instead: how much of it there is, how
long it runs, and how often it touches the two topics worth comparing across
practices.

The topic patterns and the per-column denominators are load-bearing. Changing
either silently produces a table that cannot be compared with one printed
earlier, so both are fixed here rather than exposed as options.
"""

import json
import pathlib
import re
import statistics
import typing

COST: typing.Final[re.Pattern[str]] = re.compile(
    r"\b(price|pricing|cost|expensive|afford|insurance|payment|financ|billing|charge|quote)",
    re.IGNORECASE,
)
RESULT: typing.Final[re.Pattern[str]] = re.compile(
    r"\b(result|final|finished|completed|done with|took off|removed my braces|transform)",
    re.IGNORECASE,
)

LONG_REVIEW_WORDS: typing.Final[int] = 50
NEGATIVE_AT_OR_BELOW: typing.Final[int] = 3


class Depth(typing.NamedTuple):
    """One practice's text-depth row.

    The denominators differ by column and that is deliberate. ``no_text_pct``
    and ``over_50_pct`` are shares of every review, because they describe how
    much of the whole corpus says anything at all. ``cost_pct`` and
    ``result_pct`` are shares of texted reviews only, because a bare star
    cannot mention a topic and counting it against them would just restate
    ``no_text_pct``.
    """

    practice: str
    n: int
    no_text_pct: int
    median_words: int
    over_50_pct: int
    negatives_with_text: int
    cost_pct: int
    result_pct: int


def share(count: int, total: int) -> int:
    """Return count as a whole-number percentage of total."""
    if total == 0:
        return 0
    return round(100 * count / total)


def measure(practice: str, reviews: list[dict[str, typing.Any]]) -> Depth:
    """Measure one practice's review text."""
    texts = [(review.get("text") or "").strip() for review in reviews]
    texted = [text for text in texts if text]
    lengths = [len(text.split()) for text in texts]
    written = [length for length in lengths if length]

    negatives = [
        review
        for review in reviews
        if review["rating"] <= NEGATIVE_AT_OR_BELOW and (review.get("text") or "").strip()
    ]

    return Depth(
        practice=practice,
        n=len(reviews),
        no_text_pct=share(sum(1 for length in lengths if length == 0), len(reviews)),
        median_words=int(statistics.median(written)) if written else 0,
        over_50_pct=share(sum(1 for length in lengths if length > LONG_REVIEW_WORDS), len(reviews)),
        negatives_with_text=len(negatives),
        cost_pct=share(sum(1 for text in texted if COST.search(text)), len(texted)),
        result_pct=share(sum(1 for text in texted if RESULT.search(text)), len(texted)),
    )


def measure_file(path: pathlib.Path) -> list[Depth]:
    """Measure every practice in a harvest file, deepest text first."""
    practices = json.loads(path.read_text(encoding="utf-8")).get("practices") or {}
    if not practices:
        raise ValueError(f"{path} contains no practices")

    rows = [
        measure(name, practice["reviews"])
        for name, practice in practices.items()
        if practice["reviews"]
    ]
    return sorted(rows, key=lambda row: -row.median_words)
