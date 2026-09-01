"""Command line entry point for the text-depth table."""

import argparse
import logging
import pathlib
import sys

import reviewquality.cli
import reviewquality.textdepth

logger = logging.getLogger(__name__)

HEADERS: tuple[str, ...] = (
    "practice",
    "n",
    "no text",
    "median words",
    "over 50 words",
    "negatives with text",
    "mentions cost",
    "mentions results",
)


def wikilink(practice: str) -> str:
    """Render a practice key as an Obsidian link back to its practice note.

    A key like "leone and vaughn orthodontics (madison)" names one office, but
    the vault keeps one note per practice, so the office suffix becomes the
    link's display text rather than part of its target.
    """
    if "(" not in practice:
        return f"[[{practice}]]"

    note = practice.split(" (")[0]
    return f"[[{note}\\|{practice}]]"


def render(rows: list[reviewquality.textdepth.Depth]) -> str:
    """Render the rows as the markdown table the vault note carries."""
    lines = ["| " + " | ".join(HEADERS) + " |", "| " + " | ".join("---" for _ in HEADERS) + " |"]
    for row in rows:
        lines.append(
            f"| {wikilink(row.practice)} | {row.n} | {row.no_text_pct}% | {row.median_words} "
            f"| {row.over_50_pct}% | {row.negatives_with_text} | {row.cost_pct}% "
            f"| {row.result_pct}% |"
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewtextdepth",
        description="Measure how much review text each practice has, as a markdown table.",
    )
    parser.add_argument("path", type=pathlib.Path, help="harvest JSON file")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (repeatable); logs go to stderr",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reviewquality.cli.configure_logging(args.verbose)

    if not args.path.is_file():
        logger.error("no such file: %s", args.path)
        return 1

    try:
        rows = reviewquality.textdepth.measure_file(args.path)
    except ValueError as error:
        logger.error("%s", error)
        return 1

    logger.info("measured %d practices", len(rows))
    sys.stdout.write(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
