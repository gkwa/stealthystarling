"""Command line entry point for annotating a harvest file with approximate dates."""

import argparse
import logging
import pathlib

import reviewquality.annotate
import reviewquality.cli

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewannotate",
        description="Add an approximate calendar date to every review in a harvest JSON file.",
    )
    parser.add_argument("path", type=pathlib.Path, help="harvest JSON file")
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        metavar="FILE",
        help="write here instead of rewriting the input file",
    )
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

    destination = args.output or args.path
    try:
        counts = reviewquality.annotate.annotate_file(args.path, destination)
    except ValueError as error:
        logger.error("%s", error)
        return 1

    logger.info("wrote %s (%d dated, %d undated)", destination, counts.dated, counts.undated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
