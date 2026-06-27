"""Generate the hospitality (3 hotel properties) sample data set.

Three hotels with different chart-of-account names that map to the same
standardized categories (Revenue / Payroll / Marketing / Utilities). Produced
under `data-hospitality/`. The consolidation engine doesn't change — it just
sees a different account map and a different per-entity seasonal pattern.
"""

from __future__ import annotations

import os

from generate_data import DataConfig, generate

HERE = os.path.dirname(os.path.abspath(__file__))


HOSPITALITY = DataConfig(
    name="hospitality",
    out_dir=os.path.join(HERE, "data-hospitality"),
    entities=["Marina Bay Suites", "Lakeside Inn", "Highland Lodge"],
    account_map={
        "Marina Bay Suites": {"Room Revenue": "Revenue", "F&B Revenue": "Revenue",
                              "Salaries": "Payroll", "Marketing": "Marketing",
                              "Energy": "Utilities"},
        "Lakeside Inn": {"Lodging": "Revenue", "Restaurant": "Revenue",
                         "Wages": "Payroll", "Promo": "Marketing",
                         "Utilities": "Utilities"},
        "Highland Lodge": {"Accommodation": "Revenue", "Food Service": "Revenue",
                           "Labor": "Payroll", "Advertising": "Marketing",
                           "Power": "Utilities"},
    },
    base={"Revenue": 55000, "Payroll": 22000, "Marketing": 5500, "Utilities": 4500},
    entity_mult={"Marina Bay Suites": 1.3, "Lakeside Inn": 0.9, "Highland Lodge": 1.0},
    # Different seasonal pattern — hotels peak in spring/summer travel, with a
    # bigger dip in winter than the campgrounds.
    month_factor={1: 0.6, 2: 0.65, 3: 0.85, 4: 1.05, 5: 1.2, 6: 1.4},
    yoy_growth=1.05,    # hotels grew slower than camps year-over-year
    budget_factor=1.02, # hotels budgeted slightly over actual (variance is unfavourable)
)


def main():
    generate(HOSPITALITY)


if __name__ == "__main__":
    main()
