"""Aggregate per-review rows into a per-practice quality table."""

import datetime
import logging
import typing

import polars

import reviewquality.scoring

logger = logging.getLogger(__name__)

DEFAULT_HALF_LIFE_YEARS = 3.0
DEFAULT_RECENT_WINDOW_DAYS = 730


class Summary(typing.NamedTuple):
    """The scored practice table alongside the prior it was shrunk toward."""

    table: polars.DataFrame
    prior: reviewquality.scoring.BetaPrior


def _satisfied(column: str = "rating") -> polars.Expr:
    return polars.col(column) >= reviewquality.scoring.SATISFIED_AT_OR_ABOVE


def summarise(
    reviews: polars.DataFrame,
    harvested: datetime.date,
    half_life_years: float = DEFAULT_HALF_LIFE_YEARS,
    recent_window_days: int = DEFAULT_RECENT_WINDOW_DAYS,
) -> Summary:
    """Return one scored row per practice, best first."""
    cutoff = harvested - datetime.timedelta(days=recent_window_days)

    weighted = reviews.with_columns(
        polars.col("age_years")
        .map_elements(
            lambda age: reviewquality.scoring.recency_weight(age, half_life_years),
            return_dtype=polars.Float64,
        )
        .alias("weight"),
        (polars.col("date") >= cutoff).fill_null(False).alias("is_recent"),
    )

    base = weighted.group_by("practice").agg(
        polars.col("business").first(),
        polars.len().alias("n"),
        polars.col("rating").mean().alias("mean_rating"),
        _satisfied().sum().alias("satisfied"),
        (polars.col("rating") == 1).mean().mul(100).alias("pct_one_star"),
        (polars.col("rating") <= 3).mean().mul(100).alias("pct_negative"),
        polars.col("weight").sum().alias("weighted_n"),
        polars.col("weight").filter(_satisfied()).sum().alias("weighted_satisfied"),
        polars.col("is_recent").sum().alias("n_recent"),
        _satisfied().filter(polars.col("is_recent")).mean().mul(100).alias("pct_recent_satisfied"),
        _satisfied().filter(~polars.col("is_recent")).mean().mul(100).alias("pct_older_satisfied"),
        polars.col("date").min().alias("first_review"),
        polars.col("date").median().cast(polars.Date).alias("median_review"),
        polars.col("date").max().alias("last_review"),
        (polars.col("text_length") > 0).mean().mul(100).alias("pct_with_text"),
    )

    observations = list(zip(base["satisfied"].to_list(), base["n"].to_list(), strict=True))
    prior = reviewquality.scoring.fit_beta_prior(observations)
    logger.info(
        "fitted prior mean=%.4f strength=%.1f (alpha=%.2f beta=%.2f)",
        prior.mean,
        prior.strength,
        prior.alpha,
        prior.beta,
    )

    scored = base.with_columns(
        polars.struct("satisfied", "n")
        .map_elements(
            lambda row: 100.0
            * reviewquality.scoring.shrunk_rate(row["satisfied"], row["n"], prior),
            return_dtype=polars.Float64,
        )
        .alias("adjusted"),
        polars.struct("weighted_satisfied", "weighted_n")
        .map_elements(
            lambda row: 100.0
            * reviewquality.scoring.shrunk_rate(
                row["weighted_satisfied"], row["weighted_n"], prior
            ),
            return_dtype=polars.Float64,
        )
        .alias("recency_adjusted"),
        polars.struct("satisfied", "n")
        .map_elements(
            lambda row: 100.0
            * reviewquality.scoring.wilson_lower_bound(row["satisfied"], row["n"]),
            return_dtype=polars.Float64,
        )
        .alias("wilson_low"),
    ).with_columns(
        (polars.col("pct_recent_satisfied") - polars.col("pct_older_satisfied")).alias("trend")
    )

    return Summary(table=scored.sort("recency_adjusted", descending=True), prior=prior)
