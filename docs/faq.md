# FAQ

## Why isn't this just a Power BI .pbix file?

Two reasons:
1. The kit demonstrates the *consolidation logic* — the mapping +
   identities + measures — independent of the surface. The same logic
   matches the [DAX measures](../dax-library.md) you'd put in Power BI.
2. A `.pbix` is opaque; the Python engine is auditable line-by-line and
   testable via `pytest` and the numeric eval set. That's what regulated
   clients (and serious finance teams) actually want to see.

## What if the chart of accounts doesn't match?

That's the whole point. Each entity's local account names map to the
standardized chart via `account-map.csv`. Unmapped accounts don't get
silently dropped — they're aggregated into `out/unmapped-accounts.csv`
(sorted by total amount), so the bookkeeper sees exactly what to add to
the map. See [customization.md §1](customization.md#1-swap-the-account-mapping-for-the-clients-chart).

## How do I add a new category?

Edit `CATEGORIES` and (if it's an expense) `EXPENSE_CATEGORIES` in
`consolidate.py`. Add `account-map.csv` rows that route source accounts
into the new category. The HTML dashboard and per-entity matrix pick it
up automatically.

## Why does the hospitality dataset show "unfavourable" variance?

By design — to prove the engine flags both directions. Hotels in the
`HOSPITALITY` config are budgeted at `budget_factor=1.02` (2% above
actual), so YTD variance comes out negative. Campgrounds are budgeted
at `budget_factor=0.97` (favourable). Two datasets, two variance
directions, same engine.

## How do I change the reporting period?

`python cli.py --as-of 2026-03` for YTD-through-March. Or in code,
`build_report(facts, budget, as_of_year=2026, as_of_month=3)`. The
module-level `AS_OF_YEAR` / `AS_OF_MONTH` constants are only the
defaults.

## What's the variance threshold for?

Categories whose `|variance_pct|` exceeds the threshold get an `ALERT`
badge in the dashboard and appear in `summary.alerts`. Default 10%. Use
`--variance-threshold N` to override. Tighter for stable businesses,
looser for early-stage / volatile ones.

## How do I connect to QuickBooks / Xero / NetSuite?

Write an adapter that produces the same shape (`list[dict]` of
transactions + budget). Replace the `_read(os.path.join(...))` calls
in `consolidate.py` with the adapter calls. Keep the CSV path working
so the eval cases stay valid. See
[customization.md §5](customization.md#5-move-from-csv-to-a-live-source-quickbooks-xero-netsuite).

## What's the relationship to the DAX library?

The Python engine and the DAX library compute the same measures (YTD,
MTD, PY, YoY, Budget vs Actual) — the Python is the testable spec, the
DAX is the production semantic model. When you change a measure, change
both, and re-run the eval set.

## Why doesn't the dashboard refresh automatically?

It's a static HTML file. Re-run `python run.py` (or the CLI) to
regenerate. In production, the Power BI semantic model is what refreshes
on a schedule from the live data sources — the Python engine here
proves the *measures* are right; refresh is a downstream concern.
