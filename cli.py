"""Run the consolidation engine with overrides.

    python cli.py                              # defaults
    python cli.py --as-of 2026-03              # earlier reporting period
    python cli.py --variance-threshold 2.5     # tighter alert cutoff
    python cli.py --out custom-out/            # different output dir
    python cli.py --data path/to/client-data   # different input data
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from consolidate import (  # noqa: E402
    build_per_entity_report, build_report, load_budget, load_facts,
    write_consolidated_csv, write_per_entity_csv, write_unmapped_csv,
)
from run import _money, render_html  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run the consolidation engine with parameter overrides.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--as-of", default="2026-06",
                   help="Reporting period (YYYY-MM).")
    p.add_argument("--variance-threshold", type=float, default=10.0,
                   help="Percent above/below budget that triggers an alert.")
    p.add_argument("--data", default=os.path.join(HERE, "data"),
                   help="Input data directory.")
    p.add_argument("--out", default=os.path.join(HERE, "out"),
                   help="Output directory.")
    args = p.parse_args(argv)

    year_s, month_s = args.as_of.split("-")
    year, month = int(year_s), int(month_s)

    if not os.path.exists(os.path.join(args.data, "transactions.csv")):
        import generate_data  # noqa: F401  (writes into the default data dir)
        generate_data.main()

    facts, unmapped = load_facts(args.data)
    budget = load_budget(args.data)
    report = build_report(facts, budget, as_of_year=year, as_of_month=month,
                          variance_threshold=args.variance_threshold)
    per_entity = build_per_entity_report(facts, as_of_year=year, as_of_month=month)

    os.makedirs(args.out, exist_ok=True)
    write_consolidated_csv(facts, os.path.join(args.out, "consolidated.csv"))
    write_per_entity_csv(per_entity, os.path.join(args.out, "per-entity.csv"))
    write_unmapped_csv(unmapped, os.path.join(args.out, "unmapped-accounts.csv"))
    with open(os.path.join(args.out, "dashboard.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html(report, per_entity, unmapped))

    s = report["summary"]
    print(f"As of {s['as_of']} | entities: {', '.join(s['entities'])}")
    print(f"YTD Revenue {_money(s['ytd_revenue'])} | Expenses "
          f"{_money(s['ytd_expenses'])} | Net {_money(s['ytd_net'])}")
    print(f"Variance threshold: +/-{s['variance_threshold']:.1f}%  |  "
          f"{len(unmapped)} unmapped account(s)  |  {len(s['alerts'])} alert(s)")
    for r in report["rows"]:
        flag = "  [ALERT]" if r.get("flagged") else ""
        print(f"  {r['category']:10} YTD {_money(r['ytd_actual']):>10} "
              f"vs budget {r['variance_pct']:+.1f}%  YoY {r['yoy_pct']:+.1f}%{flag}")
    if unmapped:
        print(f"\nTop unmapped accounts (showing up to 5):")
        for u in unmapped[:5]:
            print(f"  {u.entity:14} {u.source_account:25} "
                  f"${u.total_amount:>10,.2f}  ({u.count} tx)")
    print(f"\nWrote dashboard + 3 CSVs to: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
