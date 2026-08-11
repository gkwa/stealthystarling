"""Format the scored practice table for the terminal or for downstream tools."""

import io

import polars

import reviewquality.load
import reviewquality.scoring

COLUMNS: list[tuple[str, str, str]] = [
    ("business", "business", "s"),
    ("n", "n", "d"),
    ("mean_rating", "mean", ".2f"),
    ("adjusted", "adj%", ".1f"),
    ("recency_adjusted", "recent%", ".1f"),
    ("wilson_low", "floor%", ".1f"),
    ("pct_one_star", "1*%", ".1f"),
    ("pct_negative", "<=3*%", ".1f"),
    ("n_recent", "n24", "d"),
    ("pct_recent_satisfied", "sat24%", ".1f"),
    ("trend", "trend", "+.1f"),
    ("median_review", "median", "s"),
    ("last_review", "last", "s"),
]


def _cell(value: object, spec: str) -> str:
    if value is None:
        return "-"
    if spec == "s":
        return str(value)
    return format(value, spec)


def _header_note(prior: reviewquality.scoring.BetaPrior, harvest: reviewquality.load.Harvest) -> str:
    return (
        f"# harvested {harvest.harvested}  reviews {harvest.reviews.height}\n"
        f"# prior satisfaction {100 * prior.mean:.1f}% "
        f"weighing {prior.strength:.1f} pseudo-reviews\n"
        "# adj% and recent% are shrunk toward that prior; "
        "floor% is the Wilson lower bound\n"
    )


def _fixed_width(table: polars.DataFrame) -> str:
    rows = [[_cell(row[key], spec) for key, _, spec in COLUMNS] for row in table.iter_rows(named=True)]
    headers = [label for _, label, _ in COLUMNS]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
              for i in range(len(headers))]

    out = io.StringIO()
    out.write("  ".join(h.ljust(widths[i]) if i == 0 else h.rjust(widths[i])
                        for i, h in enumerate(headers)) + "\n")
    out.write("  ".join("-" * w for w in widths) + "\n")
    for row in rows:
        out.write("  ".join(c.ljust(widths[i]) if i == 0 else c.rjust(widths[i])
                            for i, c in enumerate(row)) + "\n")
    return out.getvalue()


def _markdown(table: polars.DataFrame) -> str:
    headers = [label for _, label, _ in COLUMNS]
    out = io.StringIO()
    out.write("| " + " | ".join(headers) + " |\n")
    out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    for row in table.iter_rows(named=True):
        out.write("| " + " | ".join(_cell(row[key], spec) for key, _, spec in COLUMNS) + " |\n")
    return out.getvalue()


def render(
    table: polars.DataFrame,
    prior: reviewquality.scoring.BetaPrior,
    harvest: reviewquality.load.Harvest,
    fmt: str,
) -> str:
    """Render the scored table in the requested format."""
    if fmt == "json":
        return table.write_json() + "\n"
    if fmt == "csv":
        return table.write_csv()
    if fmt == "markdown":
        return _markdown(table)

    return _header_note(prior, harvest) + _fixed_width(table)
