"""Build the consolidated model and render a self-contained HTML dashboard."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consolidate import (  # noqa: E402
    AS_OF_MONTH, AS_OF_YEAR, build_per_entity_report, build_report,
    load_budget, load_facts, write_consolidated_csv, write_per_entity_csv,
    write_unmapped_csv,
)


def _money(x):
    return f"${x:,.0f}"


def render_html(report, per_entity, unmapped) -> str:
    s = report["summary"]
    head = (
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#222}"
        "h1{font-size:1.4rem}table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "th,td{padding:.5rem .75rem;border-bottom:1px solid #eee;text-align:right}"
        "th:first-child,td:first-child{text-align:left}thead th{border-bottom:2px solid #333}"
        ".pos{color:#137333}.neg{color:#a50e0e}.cards{display:flex;gap:1rem;flex-wrap:wrap}"
        ".card{background:#f5f7fa;border-radius:8px;padding:1rem 1.25rem;min-width:160px}"
        ".card .v{font-size:1.4rem;font-weight:600}.bar{height:14px;border-radius:7px;"
        "background:#2b6cb0;display:inline-block}"
        ".alert{background:#fff7e6;border-left:4px solid #d97706;padding:.6rem 1rem;"
        "border-radius:4px;margin:.5rem 0}"
        ".badge{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:10px;"
        "background:#d97706;color:white;margin-left:.4rem}"
        "</style>"
    )
    cards = (
        f"<div class='cards'>"
        f"<div class='card'><div>YTD Revenue</div><div class='v'>{_money(s['ytd_revenue'])}</div></div>"
        f"<div class='card'><div>YTD Expenses</div><div class='v'>{_money(s['ytd_expenses'])}</div></div>"
        f"<div class='card'><div>YTD Net</div><div class='v'>{_money(s['ytd_net'])}</div></div>"
        f"<div class='card'><div>Entities</div><div class='v'>{len(s['entities'])}</div></div>"
        f"</div>"
    )
    alerts_html = ""
    if s["alerts"]:
        items = "".join(
            f"<li><strong>{a['category']}</strong>: {a['variance_pct']:+.1f}% "
            f"vs budget ({_money(a['variance'])})</li>"
            for a in s["alerts"]
        )
        alerts_html = (
            f"<div class='alert'><strong>Variance alerts</strong> "
            f"(threshold ±{s['variance_threshold']:.1f}%)<ul>{items}</ul></div>"
        )
    rows_html = ""
    for r in report["rows"]:
        vcls = "pos" if r["variance"] >= 0 else "neg"
        ycls = "pos" if r["yoy_pct"] >= 0 else "neg"
        badge = "<span class='badge'>ALERT</span>" if r.get("flagged") else ""
        rows_html += (
            f"<tr><td>{r['category']}{badge}</td>"
            f"<td>{_money(r['ytd_actual'])}</td>"
            f"<td>{_money(r['ytd_budget'])}</td>"
            f"<td class='{vcls}'>{_money(r['variance'])} ({r['variance_pct']:+.1f}%)</td>"
            f"<td>{_money(r['mtd'])}</td>"
            f"<td>{_money(r['py_ytd'])}</td>"
            f"<td class='{ycls}'>{r['yoy_pct']:+.1f}%</td></tr>"
        )
    table = (
        "<table><thead><tr><th>Category</th><th>YTD Actual</th><th>YTD Budget</th>"
        "<th>Variance</th><th>MTD</th><th>PY YTD</th><th>YoY</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )
    per_entity_html = ""
    if per_entity:
        entities = sorted({e for (e, _c) in per_entity.keys()})
        cats = sorted({c for (_e, c) in per_entity.keys()})
        header = "<tr><th>Entity</th>" + "".join(f"<th>{c}</th>" for c in cats) + "</tr>"
        body = ""
        for e in entities:
            cells = "".join(
                f"<td>{_money(per_entity.get((e, c), 0))}</td>" for c in cats
            )
            body += f"<tr><td>{e}</td>{cells}</tr>"
        per_entity_html = (
            f"<h2>By entity</h2><table><thead>{header}</thead>"
            f"<tbody>{body}</tbody></table>"
        )
    unmapped_html = ""
    if unmapped:
        rows = "".join(
            f"<tr><td>{u.entity}</td><td>{u.source_account}</td>"
            f"<td>{_money(u.total_amount)}</td><td>{u.count}</td></tr>"
            for u in unmapped[:10]
        )
        unmapped_html = (
            "<h2>Unmapped accounts <span class='badge'>ACTION</span></h2>"
            "<table><thead><tr><th>Entity</th><th>Source account</th>"
            "<th>Total</th><th>Tx count</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    rev, exp = s["ytd_revenue"], s["ytd_expenses"]
    scale = 400 / (rev or 1)
    bars = (
        f"<p>Revenue <span class='bar' style='width:{rev*scale:.0f}px'></span> {_money(rev)}<br>"
        f"Expenses <span class='bar' style='width:{exp*scale:.0f}px;background:#c05621'></span> {_money(exp)}</p>"
    )
    return (
        f"<html><head>{head}</head><body>"
        f"<h1>Consolidated Financial Dashboard - {', '.join(s['entities'])}</h1>"
        f"<p>As of {s['as_of']} - standardized chart of accounts</p>"
        f"{cards}{alerts_html}{bars}<h2>By category</h2>{table}"
        f"{per_entity_html}{unmapped_html}"
        f"<p style='color:#888;font-size:.85rem'>Generated by the consolidation "
        f"accelerator (offline sample). The real model runs in Microsoft Fabric / "
        f"Power BI - see dax-library.md.</p></body></html>"
    )


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    if not os.path.exists(os.path.join(data, "transactions.csv")):
        import generate_data
        generate_data.main()
    facts, unmapped = load_facts(data)
    budget = load_budget(data)
    report = build_report(facts, budget)
    per_entity = build_per_entity_report(facts)

    out = os.path.join(here, "out")
    os.makedirs(out, exist_ok=True)
    write_consolidated_csv(facts, os.path.join(out, "consolidated.csv"))
    write_per_entity_csv(per_entity, os.path.join(out, "per-entity.csv"))
    write_unmapped_csv(unmapped, os.path.join(out, "unmapped-accounts.csv"))
    with open(os.path.join(out, "dashboard.html"), "w", encoding="utf-8") as fh:
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
    print(f"\nWrote dashboard + 3 CSVs to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
