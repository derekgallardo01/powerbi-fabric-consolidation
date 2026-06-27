# Evaluation

Unit tests in [tests/](../tests/) check individual functions. The eval set in
[evals/golden.json](../evals/golden.json) tests **shapes of the report** — the
identities, monotonicities, and thresholds that have to hold no matter what
the input data is. They're the contract between this engine and the dashboard
that consumes it.

## What it does

[evals/run.py](../evals/run.py) loads `golden.json`, runs `build_report` /
`build_per_entity_report` / `load_facts` on the sample data with the case-
specific knobs, and checks the result. Exit code 0 if all pass, 1 otherwise
— suitable for CI gating.

```text
Eval: 10/10 passed (100%)
```

On failure you get the specific mismatch:

```text
Eval: 9/10 passed (90%)

1 failed:
  [per-entity-sums-match-consolidated]
       mismatches=[('Revenue', 732240.0, 731000.0)]
```

## Case format

Each case targets one of nine check kinds. A few examples:

```json
{"id": "ytd-revenue-positive",
 "check": "summary_field", "field": "ytd_revenue",
 "min": 700000, "max": 800000}

{"id": "no-alerts-at-default-threshold",
 "check": "alerts_count",
 "variance_threshold": 10.0, "expect": 0}

{"id": "per-entity-sums-match-consolidated",
 "check": "per_entity_sums_match_consolidated"}
```

| Check kind | What it asserts |
|------------|-----------------|
| `entities` | The consolidated `summary.entities` list matches `expect`. |
| `unmapped_count` | `len(unmapped)` from `load_facts` equals `expect`. |
| `summary_field` | A field on `summary` (e.g. `ytd_revenue`, `ytd_net`) is in `[min, max]`. |
| `alerts_count` | At `variance_threshold`, exactly `expect` alerts fire. |
| `alerts_count_min` | At `variance_threshold`, at least `min` alerts fire. |
| `row_field` | A field on a specific category's row is in `[min, max]`. |
| `per_entity_sums_match_consolidated` | Sum of per-entity values per category equals the consolidated row. |
| `march_ytd_less_than_june_ytd` | YTD-through-March revenue is less than YTD-through-June. |
| `net_equals_revenue_minus_expenses` | `ytd_net == ytd_revenue − ytd_expenses` (round to 2 dp). |

## Adding cases

Three patterns to use:

**1. Capture every real-client total as a regression test.** When you onboard a
client, agree the YTD revenue / net / per-entity totals with their finance team,
then encode them as `summary_field` / `row_field` cases with tight `min`/`max`
bounds. Anything that drifts catches your eye before it catches theirs.

**2. Capture identities, not just numbers.** Identities (like
`per_entity_sums_match_consolidated`) survive data changes — they should hold
for *every* dataset. Numbers (specific YTD revenue) need updating each period.
Lean on identities first, numbers second.

**3. Add a case the moment you find a bug.** A wrong category mapping, a
budget pivot that double-counted a row, an alert that didn't fire when it
should have — each of these is one new case.

## Workflow when tuning

1. Add the failing case(s) to `golden.json`.
2. Run `python evals/run.py` and see them fail.
3. Change the account map, the threshold, or the measure logic.
4. Re-run. Iterate until 100% pass and existing cases didn't regress.

## What an eval set is not

- **Not a substitute for tying out to source.** Eval bounds don't replace a
  manual tie-out of the engine's totals against QuickBooks / Xero for the
  client's first month.
- **Not a check on data quality.** The engine assumes `transactions.csv` is
  clean. If the bookkeeper double-entered a row, the engine sums it twice.
- **Not exhaustive.** 10 cases here are illustrative. A serious deployment
  runs with 30–50 cases per client (per-category, per-entity, per-month).
