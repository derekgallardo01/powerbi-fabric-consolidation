# Changelog

Notable changes to the Power BI / Fabric multi-entity consolidation engine.
Dates are when the change landed on `main`.

## 2026-06-27 — Live demo
- GitHub Pages live demo at
  https://derekgallardo01.github.io/powerbi-fabric-consolidation/ — three
  rendered dashboards (campgrounds default + campgrounds at tight 2% variance
  threshold + hospitality), generated on every push

## 2026-06-27 — Docker support
- Dockerfile so the engine runs via `docker run` without a Python install
- README "Run in Docker" section

## 2026-06-27 — Second dataset (hospitality / 3 hotels)
- `generate_data.py` refactored to expose `DataConfig` and a reusable
  `generate()` function
- `generate_data_hospitality.py` — 3 hotel properties with different chart
  of accounts and seasonality; budget set above actual so variance is
  unfavourable (proves the engine flags both directions)
- `data-hospitality/` CSVs
- `evals/golden-hospitality.json` (11 cases) including a variance < 0 check
- `evals/run.py` now accepts golden + data path positional args
- CI runs both eval sets on every push

## 2026-06-27 — GitHub Actions CI
- `.github/workflows/ci.yml` running pytest + eval + smoke-test on Python 3.11
- CI status badge added to README

## 2026-06-27 — Build-out: unmapped + per-entity + variance alerts
- `load_facts` now returns `(facts, unmapped)` — misses aren't silently
  dropped
- `build_per_entity_report` — drill-down behind the consolidated rows
- `build_report` grows `variance_threshold` parameter; rows over threshold
  flagged, summary collects alerts
- `cli.py` with `--as-of / --variance-threshold / --data / --out` overrides
- `evals/golden.json` (10 numeric + identity checks) + CI-gating runner
- 4 new tests covering unmapped, per-entity, threshold, AS_OF window
- `docs/architecture.md`, `customization.md`, `evaluation.md`
- `docs/sample-run.txt` (default + tight-threshold + per-entity + synthetic
  unmapped outputs)
- README expanded with architecture, sample, eval, customization sections

## 2026-06-27 — Initial public release
- Pure-stdlib consolidation engine (csv only — no pandas) for N entities
  with different charts of accounts
- Standardized chart + reporting measures (YTD, MTD, Budget vs Actual,
  Prior Year, YoY)
- HTML dashboard renderer
- `dax-library.md` for the production Power BI / Fabric model
- 6 unit tests
