"""Command line entry point."""

import argparse
import logging
import pathlib
import sys

import polars

import reviewquality.aggregate
import reviewquality.load
import reviewquality.render

logger = logging.getLogger(__name__)

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewquality",
        description="Estimate practice quality from a harvested Google reviews JSON file.",
    )
    parser.add_argument("path", type=pathlib.Path, help="harvest JSON file")
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "markdown", "csv", "json"),
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--half-life",
        type=float,
        default=reviewquality.aggregate.DEFAULT_HALF_LIFE_YEARS,
        metavar="YEARS",
        help="recency half-life in years (default: %(default)s)",
    )
    parser.add_argument(
        "--recent-window",
        type=int,
        default=reviewquality.aggregate.DEFAULT_RECENT_WINDOW_DAYS,
        metavar="DAYS",
        help="window defining a recent review (default: %(default)s)",
    )
    parser.add_argument(
        "--min-reviews",
        type=int,
        default=0,
        metavar="N",
        help="drop practices with fewer than N reviews",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (repeatable); logs go to stderr",
    )
    return parser


def configure_logging(verbosity: int) -> None:
    logging.basicConfig(
        level=LOG_LEVELS[min(verbosity, len(LOG_LEVELS) - 1)],
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)

    if not args.path.is_file():
        logger.error("no such file: %s", args.path)
        return 1

    harvest = reviewquality.load.load(args.path)
    summary = reviewquality.aggregate.summarise(
        harvest.reviews,
        harvested=harvest.harvested,
        half_life_years=args.half_life,
        recent_window_days=args.recent_window,
    )

    table = summary.table
    if args.min_reviews > 0:
        dropped = table.filter(polars.col("n") < args.min_reviews).height
        if dropped:
            logger.info("dropping %d practices under %d reviews", dropped, args.min_reviews)
        table = table.filter(polars.col("n") >= args.min_reviews)

    sys.stdout.write(reviewquality.render.render(table, summary.prior, harvest, args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
