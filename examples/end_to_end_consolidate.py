"""End-to-end multi-entity consolidation pipeline.

Production "consolidate finance data from two business entities" workflow:

  1. Load each entity's facts (transactions) and budget
  2. Map per-entity GL accounts -> the consolidated chart of accounts
  3. Build YTD / MTD / variance-vs-budget report
  4. Identify unmapped accounts (the bit nobody checks until close week)
  5. Write three outputs:
     - consolidated.csv (the dashboard's source)
     - unmapped.csv (the close-the-loop list)
     - per-entity.csv (so consolidation is auditable)

Default runs both bundled entity datasets (the campgrounds + hospitality
worked examples) and reports across both.

Usage:
    python examples/end_to_end_consolidate.py
    python examples/end_to_end_consolidate.py --entity-1 data --entity-2 data-hospitality
    python examples/end_to_end_consolidate.py --year 2025 --month 6 --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from consolidate import (  # noqa: E402
    AS_OF_MONTH, AS_OF_YEAR,
    build_per_entity_report, build_report, load_budget, load_facts,
    write_consolidated_csv, write_per_entity_csv, write_unmapped_csv,
)


def consolidate_entity(data_dir: str, label: str, as_of_year: int, as_of_month: int,
                       out_dir: Path) -> dict:
    facts, unmapped = load_facts(data_dir)
    budget = load_budget(data_dir)

    report = build_report(facts, budget, as_of_year=as_of_year, as_of_month=as_of_month)
    per_entity = build_per_entity_report(facts, as_of_year=as_of_year, as_of_month=as_of_month)

    consolidated_path = out_dir / f"{label}-consolidated.csv"
    unmapped_path = out_dir / f"{label}-unmapped.csv"
    per_entity_path = out_dir / f"{label}-per-entity.csv"
    write_consolidated_csv(facts, str(consolidated_path))
    write_unmapped_csv(unmapped, str(unmapped_path))
    write_per_entity_csv(per_entity, str(per_entity_path))

    # Variance alerts come from the rows list, flagged when |variance_pct| > threshold
    alerts = [r for r in report["rows"] if r.get("flagged")]

    return {
        "entity_label": label,
        "data_dir": data_dir,
        "facts_count": len(facts),
        "unmapped_count": len(unmapped),
        "categories_in_report": len(report["rows"]),
        "entities": report["summary"]["entities"],
        "variance_alerts": [
            {"category": r["category"], "ytd_actual": r["ytd_actual"],
             "ytd_budget": r["ytd_budget"], "variance_pct": r["variance_pct"]}
            for r in alerts
        ],
        "report_summary": {
            "ytd_revenue": report["summary"]["ytd_revenue"],
            "ytd_expenses": report["summary"]["ytd_expenses"],
            "ytd_net": report["summary"]["ytd_net"],
        },
        "output_files": [str(consolidated_path), str(unmapped_path), str(per_entity_path)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-entity consolidation pipeline demo.")
    parser.add_argument("--entity-1", default="data", help="First entity data dir.")
    parser.add_argument("--entity-2", default="data-hospitality", help="Second entity data dir.")
    parser.add_argument("--year", type=int, default=AS_OF_YEAR)
    parser.add_argument("--month", type=int, default=AS_OF_MONTH)
    parser.add_argument("--out", default=None,
                        help="Output directory. Default: temp dir cleaned at exit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cleanup_tmp = False
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="consolidate_demo_"))
        cleanup_tmp = True

    try:
        results = [
            consolidate_entity(args.entity_1, "campgrounds", args.year, args.month, out_dir),
            consolidate_entity(args.entity_2, "hospitality", args.year, args.month, out_dir),
        ]

        if args.json:
            print(json.dumps({"as_of": f"{args.year}-{args.month:02d}",
                               "entities": results}, indent=2, default=str))
            return 0

        print(f"\nConsolidating as of {args.year}-{args.month:02d}\n")
        for r in results:
            print(f"\n{'=' * 70}")
            print(f"[{r['entity_label']}] from {r['data_dir']}")
            print(f"{'=' * 70}")
            print(f"  Facts loaded:        {r['facts_count']}")
            print(f"  Unmapped accounts:   {r['unmapped_count']}")
            print(f"  Categories in report:{r['categories_in_report']}")
            print(f"  Sub-entities rolled up: {', '.join(r['entities'])}")
            print(f"\n  Financials:")
            s = r["report_summary"]
            print(f"    YTD revenue:    ${s['ytd_revenue']:>14,.2f}")
            print(f"    YTD expenses:   ${s['ytd_expenses']:>14,.2f}")
            print(f"    YTD net:        ${s['ytd_net']:>14,.2f}")
            if r["variance_alerts"]:
                print(f"\n  Variance alerts ({len(r['variance_alerts'])}):")
                for v in r["variance_alerts"]:
                    print(f"    {v['category']:30s} actual=${v['ytd_actual']:>12,.2f}  "
                          f"budget=${v['ytd_budget']:>12,.2f}  variance={v['variance_pct']:+.1f}%")
            else:
                print(f"\n  Variance alerts: none above threshold")

        print(f"\n{'=' * 70}")
        if cleanup_tmp:
            print(f"Output files written to temp dir {out_dir} (will be cleaned at exit).")
            print(f"Pass --out <dir> to keep them.")
        else:
            print(f"Output files written to {out_dir}")
    finally:
        if cleanup_tmp:
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
