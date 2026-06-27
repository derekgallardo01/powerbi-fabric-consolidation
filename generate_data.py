"""Generate deterministic sample data for the consolidation demo.

Default: three KOA campgrounds with different account names. The same machinery
is reused by `generate_data_hospitality.py` to produce a second dataset
(three hotel properties) under `data-hospitality/` — proves the engine works on
more than one industry without changing any consolidation code.

Run once to (re)create the chosen data folder. Pure stdlib, no randomness.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))


@dataclass
class DataConfig:
    """Describes one industry's mock data set."""

    name: str
    out_dir: str
    entities: list[str]
    account_map: dict[str, dict[str, str]]
    base: dict[str, float] = field(default_factory=dict)
    entity_mult: dict[str, float] = field(default_factory=dict)
    month_factor: dict[int, float] = field(default_factory=dict)
    yoy_growth: float = 1.08
    budget_factor: float = 0.97  # budget = actual * this


# ----- Default: KOA campgrounds ----------------------------------------------

CAMPGROUNDS = DataConfig(
    name="campgrounds",
    out_dir=os.path.join(HERE, "data"),
    entities=["KOA North", "KOA River", "KOA Pines"],
    account_map={
        "KOA North": {"Site Fees": "Revenue", "Store Sales": "Revenue",
                      "Staff Wages": "Payroll", "Ads": "Marketing",
                      "Power & Water": "Utilities"},
        "KOA River": {"Camping Income": "Revenue", "Shop": "Revenue",
                      "Payroll Exp": "Payroll", "Advertising": "Marketing",
                      "Utilities Exp": "Utilities"},
        "KOA Pines": {"Lodging Revenue": "Revenue", "Retail": "Revenue",
                      "Wages": "Payroll", "Marketing Spend": "Marketing",
                      "Utilities": "Utilities"},
    },
    base={"Revenue": 40000, "Payroll": 15000, "Marketing": 4000, "Utilities": 3000},
    entity_mult={"KOA North": 1.0, "KOA River": 0.8, "KOA Pines": 1.2},
    month_factor={1: 0.7, 2: 0.7, 3: 0.85, 4: 1.0, 5: 1.1, 6: 1.3},
)


# ----- Generator -------------------------------------------------------------

def amount(cfg: DataConfig, entity: str, category: str, year: int, month: int) -> float:
    base = cfg.base[category] * cfg.entity_mult[entity] * cfg.month_factor[month]
    if year == 2026:
        base *= cfg.yoy_growth
    return round(base, 2)


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def generate(cfg: DataConfig) -> None:
    rows = [(e, acct, cat) for e, m in cfg.account_map.items() for acct, cat in m.items()]
    write_csv(os.path.join(cfg.out_dir, "account-map.csv"),
              ["entity", "source_account", "category"], rows)

    tx = []
    for entity, m in cfg.account_map.items():
        rev_accts = [a for a, c in m.items() if c == "Revenue"]
        exp_accts = [(a, c) for a, c in m.items() if c != "Revenue"]
        for year in (2025, 2026):
            for month in range(1, 7):
                rev = amount(cfg, entity, "Revenue", year, month)
                tx.append((entity, f"{year}-{month:02d}-15", rev_accts[0], round(rev * 0.7, 2)))
                tx.append((entity, f"{year}-{month:02d}-15", rev_accts[1], round(rev * 0.3, 2)))
                for acct, cat in exp_accts:
                    tx.append((entity, f"{year}-{month:02d}-15", acct,
                               amount(cfg, entity, cat, year, month)))
    write_csv(os.path.join(cfg.out_dir, "transactions.csv"),
              ["entity", "date", "source_account", "amount"], tx)

    bud = []
    for entity in cfg.entities:
        for month in range(1, 7):
            for cat in cfg.base:
                target = amount(cfg, entity, cat, 2026, month) * cfg.budget_factor
                bud.append((entity, cat, f"2026-{month:02d}", round(target, 2)))
    write_csv(os.path.join(cfg.out_dir, "budget.csv"),
              ["entity", "category", "month", "amount"], bud)

    print(f"wrote {cfg.out_dir} ({cfg.name}): account-map.csv, "
          f"transactions.csv ({len(tx)} rows), budget.csv ({len(bud)} rows)")


def main():
    generate(CAMPGROUNDS)


if __name__ == "__main__":
    main()
