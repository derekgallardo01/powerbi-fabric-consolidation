"""Consolidate N entities to a standardized chart of accounts and compute the
executive measures: YTD, MTD, Budget vs Actual, Prior Year, YoY.

Also tracks unmapped accounts (entity/account combos the chart of accounts
doesn't cover) and a per-entity / per-category breakdown — the two artefacts a
CFO asks for after looking at the consolidated view.

Pure stdlib (csv only — no pandas). This mirrors what the real Fabric/Power BI
model does: map each entity's accounts to one reporting chart, build a
consolidated fact table, and express the measures (see dax-library.md for the
equivalent DAX).
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass

AS_OF_YEAR, AS_OF_MONTH = 2026, 6
PRIOR_YEAR = AS_OF_YEAR - 1
YTD_MONTHS = list(range(1, AS_OF_MONTH + 1))
CATEGORIES = ["Revenue", "Payroll", "Marketing", "Utilities"]
EXPENSE_CATEGORIES = ["Payroll", "Marketing", "Utilities"]
DEFAULT_VARIANCE_THRESHOLD = 10.0


@dataclass
class Fact:
    entity: str
    year: int
    month: int
    category: str
    amount: float


@dataclass
class Unmapped:
    entity: str
    source_account: str
    total_amount: float
    count: int


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_facts(data_dir: str):
    """Return (facts, unmapped). Unmapped rows are not silently dropped — they're
    aggregated by (entity, source_account) so the user can see exactly what the
    chart of accounts is missing.
    """
    amap = {(r["entity"], r["source_account"]): r["category"]
            for r in _read(os.path.join(data_dir, "account-map.csv"))}
    facts: list[Fact] = []
    skipped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in _read(os.path.join(data_dir, "transactions.csv")):
        cat = amap.get((r["entity"], r["source_account"]))
        amt = float(r["amount"])
        if not cat:
            skipped[(r["entity"], r["source_account"])].append(amt)
            continue
        y, m, _ = r["date"].split("-")
        facts.append(Fact(r["entity"], int(y), int(m), cat, amt))
    unmapped = [
        Unmapped(entity=e, source_account=a,
                 total_amount=round(sum(amts), 2), count=len(amts))
        for (e, a), amts in skipped.items()
    ]
    unmapped.sort(key=lambda u: u.total_amount, reverse=True)
    return facts, unmapped


def load_budget(data_dir: str) -> dict:
    budget = defaultdict(float)
    for r in _read(os.path.join(data_dir, "budget.csv")):
        y, m = r["month"].split("-")
        budget[(r["category"], int(y), int(m))] += float(r["amount"])
    return budget


def sum_by_category(facts, year, months) -> dict:
    out = defaultdict(float)
    for f in facts:
        if f.year == year and f.month in months:
            out[f.category] += f.amount
    return out


def budget_by_category(budget, year, months) -> dict:
    out = defaultdict(float)
    for (cat, y, m), amt in budget.items():
        if y == year and m in months:
            out[cat] += amt
    return out


def build_report(facts, budget,
                 as_of_year: int = AS_OF_YEAR,
                 as_of_month: int = AS_OF_MONTH,
                 variance_threshold: float = DEFAULT_VARIANCE_THRESHOLD) -> dict:
    ytd_months = list(range(1, as_of_month + 1))
    prior_year = as_of_year - 1

    ytd = sum_by_category(facts, as_of_year, ytd_months)
    mtd = sum_by_category(facts, as_of_year, [as_of_month])
    py_ytd = sum_by_category(facts, prior_year, ytd_months)
    bud_ytd = budget_by_category(budget, as_of_year, ytd_months)

    rows = []
    alerts = []
    for cat in CATEGORIES:
        a = round(ytd.get(cat, 0.0), 2)
        b = round(bud_ytd.get(cat, 0.0), 2)
        py = round(py_ytd.get(cat, 0.0), 2)
        var_pct = round((a - b) / b * 100, 1) if b else 0.0
        flagged = abs(var_pct) > variance_threshold
        rows.append({
            "category": cat,
            "ytd_actual": a,
            "ytd_budget": b,
            "variance": round(a - b, 2),
            "variance_pct": var_pct,
            "mtd": round(mtd.get(cat, 0.0), 2),
            "py_ytd": py,
            "yoy_pct": round((a - py) / py * 100, 1) if py else 0.0,
            "flagged": flagged,
        })
        if flagged:
            alerts.append({"category": cat, "variance_pct": var_pct,
                           "variance": round(a - b, 2)})

    revenue = next(r["ytd_actual"] for r in rows if r["category"] == "Revenue")
    expenses = round(sum(r["ytd_actual"] for r in rows
                         if r["category"] in EXPENSE_CATEGORIES), 2)
    summary = {
        "as_of": f"{as_of_year}-{as_of_month:02d}",
        "ytd_revenue": revenue,
        "ytd_expenses": expenses,
        "ytd_net": round(revenue - expenses, 2),
        "entities": sorted({f.entity for f in facts}),
        "variance_threshold": variance_threshold,
        "alerts": alerts,
    }
    return {"rows": rows, "summary": summary}


def build_per_entity_report(facts,
                            as_of_year: int = AS_OF_YEAR,
                            as_of_month: int = AS_OF_MONTH) -> dict:
    """Return {(entity, category): ytd_actual} for the as-of window."""
    ytd_months = set(range(1, as_of_month + 1))
    out: dict[tuple[str, str], float] = defaultdict(float)
    for f in facts:
        if f.year == as_of_year and f.month in ytd_months:
            out[(f.entity, f.category)] += f.amount
    return {k: round(v, 2) for k, v in out.items()}


def write_consolidated_csv(facts, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "year", "month", "category", "amount"])
        for f in facts:
            w.writerow([f.entity, f.year, f.month, f.category, f.amount])


def write_unmapped_csv(unmapped, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "source_account", "total_amount", "transaction_count"])
        for u in unmapped:
            w.writerow([u.entity, u.source_account, u.total_amount, u.count])


def write_per_entity_csv(per_entity, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = sorted(per_entity.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "category", "ytd_actual"])
        for (entity, category), amt in rows:
            w.writerow([entity, category, amt])
