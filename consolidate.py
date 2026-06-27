"""Consolidate N entities to a standardized chart of accounts and compute the
executive measures: YTD, MTD, Budget vs Actual, Prior Year, YoY.

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

# As-of date for the reporting period (deterministic for the demo).
AS_OF_YEAR, AS_OF_MONTH = 2026, 6
PRIOR_YEAR = AS_OF_YEAR - 1
YTD_MONTHS = list(range(1, AS_OF_MONTH + 1))
CATEGORIES = ["Revenue", "Payroll", "Marketing", "Utilities"]
EXPENSE_CATEGORIES = ["Payroll", "Marketing", "Utilities"]


@dataclass
class Fact:
    entity: str
    year: int
    month: int
    category: str
    amount: float


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_facts(data_dir: str) -> list[Fact]:
    amap = {(r["entity"], r["source_account"]): r["category"]
            for r in _read(os.path.join(data_dir, "account-map.csv"))}
    facts = []
    for r in _read(os.path.join(data_dir, "transactions.csv")):
        cat = amap.get((r["entity"], r["source_account"]))
        if not cat:
            continue  # unmapped account — flagged in a real run
        y, m, _ = r["date"].split("-")
        facts.append(Fact(r["entity"], int(y), int(m), cat, float(r["amount"])))
    return facts


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


def build_report(facts, budget) -> dict:
    ytd = sum_by_category(facts, AS_OF_YEAR, YTD_MONTHS)
    mtd = sum_by_category(facts, AS_OF_YEAR, [AS_OF_MONTH])
    py_ytd = sum_by_category(facts, PRIOR_YEAR, YTD_MONTHS)
    bud_ytd = budget_by_category(budget, AS_OF_YEAR, YTD_MONTHS)

    rows = []
    for cat in CATEGORIES:
        a = round(ytd.get(cat, 0.0), 2)
        b = round(bud_ytd.get(cat, 0.0), 2)
        py = round(py_ytd.get(cat, 0.0), 2)
        rows.append({
            "category": cat,
            "ytd_actual": a,
            "ytd_budget": b,
            "variance": round(a - b, 2),
            "variance_pct": round((a - b) / b * 100, 1) if b else 0.0,
            "mtd": round(mtd.get(cat, 0.0), 2),
            "py_ytd": py,
            "yoy_pct": round((a - py) / py * 100, 1) if py else 0.0,
        })

    revenue = next(r["ytd_actual"] for r in rows if r["category"] == "Revenue")
    expenses = round(sum(r["ytd_actual"] for r in rows
                         if r["category"] in EXPENSE_CATEGORIES), 2)
    summary = {
        "ytd_revenue": revenue,
        "ytd_expenses": expenses,
        "ytd_net": round(revenue - expenses, 2),
        "entities": sorted({f.entity for f in facts}),
    }
    return {"rows": rows, "summary": summary}


def write_consolidated_csv(facts, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entity", "year", "month", "category", "amount"])
        for f in facts:
            w.writerow([f.entity, f.year, f.month, f.category, f.amount])
