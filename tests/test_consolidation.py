import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import generate_data  # noqa: E402
from consolidate import (  # noqa: E402
    AS_OF_YEAR, YTD_MONTHS, build_report, load_budget, load_facts,
    sum_by_category,
)

generate_data.main()  # ensure data exists/up to date
DATA = os.path.join(ROOT, "data")
FACTS, UNMAPPED = load_facts(DATA)
BUDGET = load_budget(DATA)
REPORT = build_report(FACTS, BUDGET)


def test_all_transactions_mapped():
    # every transaction row maps to a category (none dropped)
    import csv
    raw = list(csv.DictReader(open(os.path.join(DATA, "transactions.csv"))))
    assert len(FACTS) == len(raw)


def test_three_entities_consolidated():
    assert REPORT["summary"]["entities"] == ["KOA North", "KOA Pines", "KOA River"]


def test_ytd_revenue_matches_manual_sum():
    manual = sum(f.amount for f in FACTS
                 if f.year == AS_OF_YEAR and f.month in YTD_MONTHS
                 and f.category == "Revenue")
    assert round(manual, 2) == REPORT["summary"]["ytd_revenue"]


def test_budget_vs_actual_variance_is_consistent():
    row = next(r for r in REPORT["rows"] if r["category"] == "Revenue")
    assert round(row["ytd_actual"] - row["ytd_budget"], 2) == row["variance"]
    # budgets were set 3% under actual, so revenue variance should be positive
    assert row["variance"] > 0


def test_net_equals_revenue_minus_expenses():
    s = REPORT["summary"]
    assert round(s["ytd_revenue"] - s["ytd_expenses"], 2) == s["ytd_net"]


def test_prior_year_present_and_growth_positive():
    row = next(r for r in REPORT["rows"] if r["category"] == "Revenue")
    assert row["py_ytd"] > 0
    # current year grows 8% over prior year in the generator
    assert row["yoy_pct"] > 0
