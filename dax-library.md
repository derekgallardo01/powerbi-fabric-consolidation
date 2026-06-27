# DAX measure library

The reusable measures for the real Power BI / Fabric model. The offline `run.py`
computes the same numbers in Python; these are what you paste into the semantic
model. Assumes a `Facts[Amount]` table with a `Date` dimension (`Dates[Date]`) and
a standardized `Accounts[Category]`.

```dax
-- Base
Total Amount = SUM ( Facts[Amount] )

-- Year-to-date (respects the report's as-of date)
YTD Actual =
TOTALYTD ( [Total Amount], Dates[Date] )

-- Month-to-date
MTD Actual =
TOTALMTD ( [Total Amount], Dates[Date] )

-- Prior year (same period last year)
PY YTD =
CALCULATE ( [YTD Actual], SAMEPERIODLASTYEAR ( Dates[Date] ) )

-- Year-over-year growth %
YoY % =
DIVIDE ( [YTD Actual] - [PY YTD], [PY YTD] )

-- Budget (from a Budget table at category/month grain)
YTD Budget =
TOTALYTD ( SUM ( Budget[Amount] ), Dates[Date] )

-- Budget vs Actual variance and %
Budget Variance = [YTD Actual] - [YTD Budget]
Budget Variance % = DIVIDE ( [Budget Variance], [YTD Budget] )

-- Net income (Revenue minus expense categories)
Net Income =
CALCULATE ( [Total Amount], Accounts[Category] = "Revenue" )
  - CALCULATE ( [Total Amount], Accounts[Category] IN { "Payroll", "Marketing", "Utilities" } )
```

**Notes**
- Build a proper `Dates` table and mark it as the date table so time-intelligence
  works.
- The account mapping (entity-specific account → standardized category) is a
  dimension you maintain — see `account-mapping.example.csv`. In Fabric, do the
  mapping in the dataflow/pipeline so the model stays clean.
