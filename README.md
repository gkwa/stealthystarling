# reviewquality

Estimate practice quality from a harvested Google reviews JSON file.

## Cheatsheet

```
uv run reviewquality "orthodontist reviews.json"              # scored table
uv run reviewquality "orthodontist reviews.json" -f markdown  # markdown
uv run reviewquality "orthodontist reviews.json" -f csv       # csv
uv run reviewquality "orthodontist reviews.json" -f json      # json
uv run reviewquality "orthodontist reviews.json" -v           # logs to stderr
uv run reviewquality "orthodontist reviews.json" -vv          # debug logs
uv run reviewquality "orthodontist reviews.json" --min-reviews 30
uv run reviewquality "orthodontist reviews.json" --half-life 2
uv run reviewquality "orthodontist reviews.json" --recent-window 365
```

## Why not just rank by mean rating

Roughly nine in ten reviews are five stars, so every practice's mean sits in a
narrow band and the gaps between them are mostly noise.

Sample sizes run from single digits into the hundreds, so an unadjusted rate
lets a practice with six reviews outrank one with nine hundred.

So the tool scores the satisfaction rate — the share of reviews at four stars
or better — instead of averaging stars, then shrinks that rate toward a Beta
prior fitted across all practices by beta-binomial maximum likelihood. Thin
evidence gets pulled toward the field; heavy evidence barely moves.

## Columns

- `mean` — raw mean star rating, shown for reference only
- `adj%` — satisfaction rate shrunk toward the fitted prior
- `recent%` — the same, with reviews decayed on a half-life (default 3 years)
- `floor%` — Wilson lower bound, a pessimistic rate that punishes small samples
- `1*%`, `<=3*%` — dissatisfaction rates, the most discriminating raw signal
- `n24`, `sat24%`, `trend` — recent-window volume, satisfaction, and the shift
  against the older cohort

## Dates

Google reports ages relatively, so dates are estimated as the harvest date
minus the stated offset. The buckets are coarse — anything from 12 to 23 months
reads as "a year ago" — so older dates carry roughly six months of error. Use
them for cohorts and trends, not for precise timelines.
