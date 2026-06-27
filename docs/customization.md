# Customization

Six things you'll typically tune per client.

## 1. Swap the account mapping for the client's chart

Edit [data/account-map.csv](../data/account-map.csv) — one row per `(entity,
source_account, category)`. The sample
[account-mapping.example.csv](../account-mapping.example.csv) is a clean
starting template; copy it and fill in real source-account names from the
client's GL extract.

The pipeline tells you what to add: after a first run,
`out/unmapped-accounts.csv` lists every (entity, source_account) combo that
wasn't covered. Send that to the bookkeeper, get the right category for each,
add them to the map, re-run.

## 2. Change the reporting period

```bash
python cli.py --as-of 2026-03
```

Or in code:

```python
report = build_report(facts, budget, as_of_year=2026, as_of_month=3)
per_entity = build_per_entity_report(facts, as_of_year=2026, as_of_month=3)
```

The defaults in [consolidate.py](../consolidate.py) (`AS_OF_YEAR`,
`AS_OF_MONTH`) are only used when no override is passed.

## 3. Add a new category

Edit `CATEGORIES` and (if it's an expense) `EXPENSE_CATEGORIES` in
[consolidate.py](../consolidate.py):

```python
CATEGORIES = ["Revenue", "Payroll", "Marketing", "Utilities", "Insurance"]
EXPENSE_CATEGORIES = ["Payroll", "Marketing", "Utilities", "Insurance"]
```

Then add `account-map.csv` rows that route source accounts into the new
category. The HTML dashboard and per-entity matrix pick it up automatically.

## 4. Variance threshold — global vs per-category

Default is global: one `variance_threshold` applies to every category. If you
want different cutoffs (e.g. ±2% on Revenue, ±15% on Marketing), the cleanest
path is to add a `per_category_thresholds` dict in `build_report`:

```python
def build_report(facts, budget, ..., variance_threshold=10.0,
                 per_category_thresholds=None):
    per_category_thresholds = per_category_thresholds or {}
    ...
    for cat in CATEGORIES:
        threshold = per_category_thresholds.get(cat, variance_threshold)
        flagged = abs(var_pct) > threshold
        ...
```

Pass `{"Revenue": 2.0, "Marketing": 15.0}` from the CLI / production caller.

## 5. Move from CSV to a live source (QuickBooks, Xero, NetSuite)

`load_facts` and `load_budget` only know about CSV with specific columns. To
read from a live API:

1. Write an adapter that produces the same shape:
   `list[{"entity", "date", "source_account", "amount"}]` for transactions,
   `list[{"category", "month", "amount"}]` for budget.
2. Replace the `_read(os.path.join(...))` calls with the adapter calls.
3. Cache the adapter output to a local CSV the first time so dev / eval runs
   stay offline (a real Fabric refresh schedule already handles caching, but
   this engine doesn't).

Keep the existing CSV path working — eval cases read from CSV and adapter bugs
shouldn't break the regression net.

## 6. Tie the offline engine to the DAX library

The measures computed by `build_report` mirror the DAX measures in
[dax-library.md](../dax-library.md):

| Python (consolidate.py) | DAX (Fabric / Power BI) |
|-------------------------|-------------------------|
| `sum_by_category(facts, year, ytd_months)` | `YTD = TOTALYTD(SUM(...), Calendar[Date])` |
| `sum_by_category(facts, year, [as_of_month])` | `MTD = TOTALMTD(SUM(...), Calendar[Date])` |
| `sum_by_category(facts, prior_year, ytd_months)` | `PY YTD = TOTALYTD(SUM(...), SAMEPERIODLASTYEAR(Calendar[Date]))` |
| `(a - b) / b * 100` | `Variance % = DIVIDE([Actual] - [Budget], [Budget])` |

When you change a measure, change both — and re-run `python evals/run.py` plus
a quick eyeball of the Power BI tile to confirm they still match.

## Validating any change

```bash
python -m pytest -q
python evals/run.py
python run.py
```

If you changed the chart of accounts or the budget, **add expected totals to
[evals/golden.json](../evals/golden.json) before changing the code** — the eval
set is the regression net that catches "I forgot to update the budget too".
