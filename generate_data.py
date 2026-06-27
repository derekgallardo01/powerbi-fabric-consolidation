"""Generate deterministic sample data for the consolidation demo.

Three mock "QuickBooks companies" (KOA campgrounds) with *different* account
names that map to one standardized chart of accounts. Emits monthly GL totals for
2025 (prior year) and 2026-01..06 (current year, as-of 2026-06-27), plus budgets.

Run once to (re)create data/. Pure stdlib, no randomness — fully reproducible.
"""

from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

ENTITIES = ["KOA North", "KOA River", "KOA Pines"]

# Standardized categories and each entity's local account name → category.
ACCOUNT_MAP = {
    "KOA North": {"Site Fees": "Revenue", "Store Sales": "Revenue",
                  "Staff Wages": "Payroll", "Ads": "Marketing", "Power & Water": "Utilities"},
    "KOA River": {"Camping Income": "Revenue", "Shop": "Revenue",
                  "Payroll Exp": "Payroll", "Advertising": "Marketing", "Utilities Exp": "Utilities"},
    "KOA Pines": {"Lodging Revenue": "Revenue", "Retail": "Revenue",
                  "Wages": "Payroll", "Marketing Spend": "Marketing", "Utilities": "Utilities"},
}

# Base monthly amount per (entity, category). Revenue positive; expenses positive
# (sign handled by category at report time).
BASE = {
    "Revenue": 40000, "Payroll": 15000, "Marketing": 4000, "Utilities": 3000,
}
# Deterministic per-entity multiplier and per-month seasonal factor.
ENTITY_MULT = {"KOA North": 1.0, "KOA River": 0.8, "KOA Pines": 1.2}
# Summer season (camp business) — higher in Jun.
MONTH_FACTOR = {1: 0.7, 2: 0.7, 3: 0.85, 4: 1.0, 5: 1.1, 6: 1.3}


def amount(entity, category, year, month):
    base = BASE[category] * ENTITY_MULT[entity] * MONTH_FACTOR[month]
    # current year grows 8% over prior year
    if year == 2026:
        base *= 1.08
    # split revenue across the entity's two revenue accounts handled by caller
    return round(base, 2)


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    os.makedirs(DATA, exist_ok=True)

    # account map
    rows = [(e, acct, cat) for e, m in ACCOUNT_MAP.items() for acct, cat in m.items()]
    write_csv(os.path.join(DATA, "account-map.csv"),
              ["entity", "source_account", "category"], rows)

    # transactions (monthly GL totals)
    tx = []
    for entity, m in ACCOUNT_MAP.items():
        # revenue split across the two revenue accounts 70/30
        rev_accts = [a for a, c in m.items() if c == "Revenue"]
        exp_accts = [(a, c) for a, c in m.items() if c != "Revenue"]
        for year in (2025, 2026):
            months = range(1, 7)  # Jan..Jun both years (YTD window)
            for month in months:
                rev = amount(entity, "Revenue", year, month)
                tx.append((entity, f"{year}-{month:02d}-15", rev_accts[0], round(rev * 0.7, 2)))
                tx.append((entity, f"{year}-{month:02d}-15", rev_accts[1], round(rev * 0.3, 2)))
                for acct, cat in exp_accts:
                    tx.append((entity, f"{year}-{month:02d}-15", acct,
                               amount(entity, cat, year, month)))
    write_csv(os.path.join(DATA, "transactions.csv"),
              ["entity", "date", "source_account", "amount"], tx)

    # budgets (current year only, by category, slightly above prior-year run-rate)
    bud = []
    for entity in ENTITIES:
        for month in range(1, 7):
            for cat in BASE:
                target = amount(entity, cat, 2026, month) * 0.97  # budget set 3% under actual
                bud.append((entity, cat, f"2026-{month:02d}", round(target, 2)))
    write_csv(os.path.join(DATA, "budget.csv"),
              ["entity", "category", "month", "amount"], bud)

    print(f"wrote {DATA}: account-map.csv, transactions.csv ({len(tx)} rows), "
          f"budget.csv ({len(bud)} rows)")


if __name__ == "__main__":
    main()
