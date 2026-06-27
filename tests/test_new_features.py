import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from consolidate import (  # noqa: E402
    build_per_entity_report, build_report, load_budget, load_facts,
)

DATA = os.path.join(ROOT, "data")
FACTS, _ = load_facts(DATA)
BUDGET = load_budget(DATA)


def _write_csvs(amap, transactions):
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "account-map.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "source_account", "category"])
        w.writerows(amap)
    with open(os.path.join(tmp, "transactions.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "date", "source_account", "amount"])
        w.writerows(transactions)
    return tmp


def test_unmapped_aggregated_by_entity_and_account():
    tmp = _write_csvs(
        amap=[("A", "Revenue", "Revenue")],
        transactions=[
            ("A", "2026-01-15", "Revenue", "100"),
            ("A", "2026-02-15", "MysteryAccount", "300"),
            ("A", "2026-03-15", "MysteryAccount", "200"),
            ("A", "2026-04-15", "OtherMystery", "50"),
        ],
    )
    facts, unmapped = load_facts(tmp)
    assert len(facts) == 1
    by = {(u.entity, u.source_account): u for u in unmapped}
    assert (("A", "MysteryAccount") in by) and (("A", "OtherMystery") in by)
    assert by[("A", "MysteryAccount")].total_amount == 500
    assert by[("A", "MysteryAccount")].count == 2
    # Sorted by total_amount desc
    assert unmapped[0].source_account == "MysteryAccount"


def test_per_entity_totals_sum_to_consolidated():
    per = build_per_entity_report(FACTS)
    by_category = {}
    for (_e, cat), amt in per.items():
        by_category[cat] = by_category.get(cat, 0) + amt
    report = build_report(FACTS, BUDGET)
    for row in report["rows"]:
        assert round(by_category.get(row["category"], 0), 2) == row["ytd_actual"]


def test_variance_threshold_flags_only_above_cutoff():
    # Tight threshold: more categories flagged.
    tight = build_report(FACTS, BUDGET, variance_threshold=1.0)
    loose = build_report(FACTS, BUDGET, variance_threshold=20.0)
    assert len(tight["summary"]["alerts"]) >= len(loose["summary"]["alerts"])
    for row in tight["rows"]:
        assert row["flagged"] == (abs(row["variance_pct"]) > 1.0)


def test_as_of_month_changes_ytd_window():
    march = build_report(FACTS, BUDGET, as_of_year=2026, as_of_month=3)
    june = build_report(FACTS, BUDGET, as_of_year=2026, as_of_month=6)
    rev_mar = next(r["ytd_actual"] for r in march["rows"] if r["category"] == "Revenue")
    rev_jun = next(r["ytd_actual"] for r in june["rows"] if r["category"] == "Revenue")
    assert rev_mar < rev_jun  # YTD-through-March < YTD-through-June
