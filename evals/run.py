"""Run the consolidation engine against a golden numeric eval set.

    python evals/run.py                                       # default: golden.json + data/
    python evals/run.py golden-hospitality.json data-hospitality

Exit code 0 if all cases pass, 1 otherwise. Each case targets one of the report
shapes: consolidated totals, unmapped count, alert counts at a threshold,
per-entity sum identity, YTD-window monotonicity, or net-identity.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from consolidate import (  # noqa: E402
    build_per_entity_report, build_report, load_budget, load_facts,
)


def _check(case: dict, facts: list, budget: dict) -> tuple[bool, str]:
    kind = case["check"]
    if kind == "entities":
        report = build_report(facts, budget)
        actual = report["summary"]["entities"]
        return (actual == case["expect"],
                f"entities={actual} expected={case['expect']}")

    if kind == "unmapped_count":
        data_dir = case.get("_data_dir", os.path.join(ROOT, "data"))
        _, unmapped = load_facts(data_dir)
        return (len(unmapped) == case["expect"],
                f"unmapped_count={len(unmapped)} expected={case['expect']}")

    if kind == "summary_field":
        report = build_report(facts, budget)
        v = report["summary"][case["field"]]
        ok = (case.get("min", float("-inf")) <= v <= case.get("max", float("inf")))
        return (ok, f"{case['field']}={v} expected in [{case.get('min')}, {case.get('max')}]")

    if kind == "alerts_count":
        report = build_report(facts, budget,
                              variance_threshold=case["variance_threshold"])
        n = len(report["summary"]["alerts"])
        return (n == case["expect"],
                f"alerts_count={n} expected={case['expect']} at threshold {case['variance_threshold']}")

    if kind == "alerts_count_min":
        report = build_report(facts, budget,
                              variance_threshold=case["variance_threshold"])
        n = len(report["summary"]["alerts"])
        return (n >= case["min"],
                f"alerts_count={n} expected>={case['min']} at threshold {case['variance_threshold']}")

    if kind == "row_field":
        report = build_report(facts, budget)
        row = next(r for r in report["rows"] if r["category"] == case["category"])
        v = row[case["field"]]
        ok = (case.get("min", float("-inf")) <= v <= case.get("max", float("inf")))
        return (ok, f"{case['category']}.{case['field']}={v} expected in [{case.get('min')}, {case.get('max')}]")

    if kind == "per_entity_sums_match_consolidated":
        per = build_per_entity_report(facts)
        by_cat: dict[str, float] = {}
        for (_e, cat), amt in per.items():
            by_cat[cat] = by_cat.get(cat, 0) + amt
        report = build_report(facts, budget)
        mismatches = [
            (r["category"], r["ytd_actual"], round(by_cat.get(r["category"], 0), 2))
            for r in report["rows"]
            if round(by_cat.get(r["category"], 0), 2) != r["ytd_actual"]
        ]
        return (not mismatches, f"mismatches={mismatches}")

    if kind == "march_ytd_less_than_june_ytd":
        m = build_report(facts, budget, as_of_year=2026, as_of_month=3)
        j = build_report(facts, budget, as_of_year=2026, as_of_month=6)
        mr = m["summary"]["ytd_revenue"]
        jr = j["summary"]["ytd_revenue"]
        return (mr < jr, f"march_ytd_rev={mr} june_ytd_rev={jr} (expected march<june)")

    if kind == "net_equals_revenue_minus_expenses":
        report = build_report(facts, budget)
        s = report["summary"]
        return (round(s["ytd_revenue"] - s["ytd_expenses"], 2) == s["ytd_net"],
                f"rev={s['ytd_revenue']} exp={s['ytd_expenses']} net={s['ytd_net']}")

    return (False, f"unknown check {kind!r}")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    golden_name = argv[0] if len(argv) > 0 else "golden.json"
    data_rel = argv[1] if len(argv) > 1 else "data"

    golden_path = (golden_name if os.path.isabs(golden_name)
                   else os.path.join(HERE, golden_name))
    data_path = (data_rel if os.path.isabs(data_rel)
                 else os.path.join(ROOT, data_rel))

    with open(golden_path, encoding="utf-8") as fh:
        cases = json.load(fh)
    # Generator runs on demand for whichever dataset is being eval'd.
    if not os.path.exists(os.path.join(data_path, "transactions.csv")):
        if os.path.basename(data_path) == "data-hospitality":
            import generate_data_hospitality
            generate_data_hospitality.main()
        else:
            import generate_data
            generate_data.main()
    facts, _ = load_facts(data_path)
    budget = load_budget(data_path)

    passed, failed = [], []
    for case in cases:
        case["_data_dir"] = data_path
        ok, detail = _check(case, facts, budget)
        rec = {"id": case["id"], "detail": detail}
        (passed if ok else failed).append(rec)

    total = len(cases)
    rate = (len(passed) / total * 100) if total else 0.0
    label = os.path.basename(golden_path)
    print(f"Eval ({label}): {len(passed)}/{total} passed ({rate:.0f}%)")
    if failed:
        print(f"\n{len(failed)} failed:")
        for f in failed:
            print(f"  [{f['id']}]")
            print(f"       {f['detail']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
