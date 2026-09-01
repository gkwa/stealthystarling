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
uv run reviewquality "orthodontist reviews.json" --prior 8.950350,0.534357
uv run reviewannotate "orthodontist reviews.json"             # add date_approx in place
uv run reviewannotate "orthodontist reviews.json" -o out.json # write a copy instead
uv run reviewtextdepth "orthodontist reviews.json"            # text-depth markdown table
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

## Text depth

`reviewtextdepth` is the other half of the picture. The scored table is
computed from the star and the date alone, so it cannot tell hundreds of bare
five-star ratings from hundreds of paragraphs. This one reads the text: how
much of it exists, how long it runs, and how often it mentions cost or a
finished result.

Two details are load-bearing and are therefore fixed in the code rather than
exposed as flags.

The topic patterns, both case-insensitive:

- cost: `\b(price|pricing|cost|expensive|afford|insurance|payment|financ|billing|charge|quote)`
- result: `\b(result|final|finished|completed|done with|took off|removed my braces|transform)`

The denominators differ by column. `no text` and `over 50 words` are shares of
every review, because they describe how much of the corpus says anything at
all. `mentions cost` and `mentions results` are shares of texted reviews only,
since a bare star cannot mention a topic. `median words` is over texted
reviews.

Changing either would produce a table that cannot be compared against one
printed earlier, which is the whole reason this is a committed script rather
than an ad hoc one.

## Pinning the prior

By default the prior is refitted every run, across whatever practices the file
holds. That is the right behaviour for a fresh analysis and the wrong one for
a table that has already been written down: adding a practice moves `adj%` and
`recent%` for every practice already in it, so an append becomes a rewrite.

`--prior ALPHA,BETA` pins the shrinkage target instead. Passing the fit that
produced an existing table keeps a newly added practice comparable to it while
leaving the other rows alone.

The 34-practice fit behind the current orthodontist table is
`--prior 8.950350,0.534357`, which reproduces that table to within 4e-06 on
every numeric cell.

## Dates

Google reports ages relatively, so dates are estimated as the harvest date
minus the stated offset. The buckets are coarse — anything from 12 to 23 months
reads as "a year ago" — so older dates carry roughly six months of error. Use
them for cohorts and trends, not for precise timelines.

`reviewannotate` writes that estimate back into the harvest file as a
`date_approx` field beside each review's relative `date`, so the JSON carries
calendar dates without a rerun of the scorer. Rerunning it is safe: an existing
`date_approx` is recomputed from the current harvest date rather than
duplicated.
