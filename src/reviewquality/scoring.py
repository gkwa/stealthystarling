"""Statistics for turning skewed, unevenly sampled star ratings into a ranking.

Two problems make the raw mean rating useless as a quality estimate.

Nearly nine in ten reviews are five stars, so every practice's mean lands in a
narrow band near the top of the scale and small differences are mostly noise.

Sample sizes span two orders of magnitude, so an unshrunk rate lets a handful
of reviews outrank hundreds.

The fix is to score satisfaction as a rate rather than an average, then shrink
that rate toward a prior fitted across all practices.
"""

import math
import typing

SATISFIED_AT_OR_ABOVE: typing.Final[int] = 4


class BetaPrior(typing.NamedTuple):
    """A fitted Beta prior over the per-practice satisfaction rate."""

    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def strength(self) -> float:
        """Pseudo-count weight: how many real reviews it takes to outvote the prior."""
        return self.alpha + self.beta


def _log_beta(alpha: float, beta: float) -> float:
    return math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)


def _log_likelihood(prior: BetaPrior, observations: list[tuple[int, int]]) -> float:
    """Beta-binomial marginal log-likelihood of every practice under one prior."""
    total = 0.0
    for successes, trials in observations:
        total += _log_beta(prior.alpha + successes, prior.beta + trials - successes)
        total -= _log_beta(prior.alpha, prior.beta)
    return total


def fit_beta_prior(
    observations: list[tuple[int, int]],
    grid_steps: int = 240,
    refinements: int = 2,
) -> BetaPrior:
    """Fit a Beta prior by maximising the beta-binomial marginal likelihood.

    Each observation is a (satisfied, total) count for one practice. A
    coarse-to-fine grid search over (mean, strength) is plenty here: the
    surface is smooth and there are only a few dozen practices.
    """
    if not observations:
        raise ValueError("cannot fit a prior without observations")

    low_strength, high_strength = 0.5, 400.0
    best: tuple[float, BetaPrior] | None = None

    for _ in range(refinements):
        for i in range(grid_steps + 1):
            mean = 0.5 + 0.4999 * i / grid_steps
            for j in range(grid_steps + 1):
                strength = low_strength * (high_strength / low_strength) ** (j / grid_steps)
                candidate = BetaPrior(mean * strength, (1.0 - mean) * strength)
                score = _log_likelihood(candidate, observations)
                if best is None or score > best[0]:
                    best = (score, candidate)

        assert best is not None
        low_strength = max(0.3, best[1].strength / 3.0)
        high_strength = best[1].strength * 3.0

    assert best is not None
    return best[1]


def shrunk_rate(successes: float, trials: float, prior: BetaPrior) -> float:
    """Posterior mean satisfaction rate, shrunk toward the fitted prior."""
    return (successes + prior.alpha) / (trials + prior.strength)


def wilson_lower_bound(successes: int, trials: int, z: float = 1.96) -> float:
    """Lower end of the Wilson score interval: a pessimistic, size-aware rate."""
    if trials == 0:
        return 0.0

    observed = successes / trials
    denominator = 1.0 + z * z / trials
    centre = observed + z * z / (2.0 * trials)
    radius = z * math.sqrt((observed * (1.0 - observed) + z * z / (4.0 * trials)) / trials)
    return (centre - radius) / denominator


def recency_weight(age_years: float | None, half_life_years: float, fallback: float = 3.0) -> float:
    """Exponential decay weight so stale reviews count for less than fresh ones."""
    age = fallback if age_years is None else age_years
    return math.exp(-math.log(2.0) * age / half_life_years)
