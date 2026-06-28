# Getting started

A 5-minute walkthrough — no Power BI or Microsoft Fabric tenant required.

## 1. Clone and run the default demo

```bash
git clone https://github.com/derekgallardo01/powerbi-fabric-consolidation.git
cd powerbi-fabric-consolidation
python run.py
```

This consolidates 3 KOA campgrounds, writes `out/dashboard.html`,
`out/consolidated.csv`, `out/per-entity.csv`, and
`out/unmapped-accounts.csv` (empty if everything maps). Open
`out/dashboard.html` in a browser.

## 2. Run the eval set

```bash
python evals/run.py
```

`Eval (golden.json): 10/10 passed (100%)`. There's also a hospitality
dataset (3 hotels):

```bash
python evals/run.py golden-hospitality.json data-hospitality
```

`Eval (golden-hospitality.json): 11/11 passed (100%)`.

## 3. Try the CLI overrides

```bash
python cli.py --as-of 2026-03                 # earlier reporting period
python cli.py --variance-threshold 2.0        # tighter alerts (surfaces ALERT badges)
python cli.py --data data-hospitality         # the hotels dataset
python cli.py --data data-hospitality --out out-hospitality
```

## 4. See the live demos

The CI deploys both dashboards on every push:

- https://derekgallardo01.github.io/powerbi-fabric-consolidation/

Three rendered dashboards (campgrounds default · campgrounds with tight
variance threshold · hospitality), no Python required.

## 5. Run in Docker (optional)

```bash
docker build -t powerbi-fabric-consolidation .
docker run --rm -v $(pwd)/out:/app/out powerbi-fabric-consolidation
```

`-v` mounts your local `out/` so the generated dashboard is on your host
filesystem, not stuck in the container.

## What to read next

- [Architecture](architecture.md) · [Customization](customization.md) ·
  [Evaluation](evaluation.md) · [Diagrams](diagrams.md) · [FAQ](faq.md)

## Bringing it to a real client

The Python engine proves the **logic**. The matching DAX measures live
in [`dax-library.md`](../dax-library.md) — that's what you put in the
Power BI semantic model. Same identities, same outputs.
