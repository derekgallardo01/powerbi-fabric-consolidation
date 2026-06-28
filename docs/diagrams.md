# Diagrams

Beyond the inline ones in [architecture.md](architecture.md).

## 1. Class-ish model — data shapes flowing through the engine

```mermaid
classDiagram
    class Fact {
      +str entity
      +int year
      +int month
      +str category
      +float amount
    }
    class Unmapped {
      +str entity
      +str source_account
      +float total_amount
      +int count
    }
    class DataConfig {
      +str name
      +str out_dir
      +list~str~ entities
      +dict account_map
      +dict base
      +dict entity_mult
      +dict month_factor
      +float yoy_growth
      +float budget_factor
    }
    class Report {
      +list~dict~ rows
      +dict summary
    }
    class Summary {
      +str as_of
      +float ytd_revenue
      +float ytd_expenses
      +float ytd_net
      +list~str~ entities
      +float variance_threshold
      +list~Alert~ alerts
    }
    class Alert {
      +str category
      +float variance_pct
      +float variance
    }

    DataConfig --> Fact : generate()
    DataConfig --> Unmapped : load_facts()
    Fact --> Report : build_report()
    Report --> Summary
    Summary --> Alert
```

## 2. Data flow — from CSVs through to outputs

```mermaid
flowchart LR
    subgraph IN["Inputs (per dataset)"]
      AM[("account-map.csv")]
      TX[("transactions.csv")]
      BG[("budget.csv")]
    end

    subgraph LOAD["Loaders"]
      LF["load_facts()"]
      LB["load_budget()"]
    end

    subgraph COMPUTE["Compute"]
      BR["build_report()"]
      BPE["build_per_entity_report()"]
    end

    subgraph OUT["Outputs (per run)"]
      DH["dashboard.html"]
      CC["consolidated.csv"]
      PEC["per-entity.csv"]
      UAC["unmapped-accounts.csv"]
    end

    AM --> LF
    TX --> LF
    BG --> LB
    LF -->|facts| BR
    LF -->|unmapped| UAC
    LF -->|facts| BPE
    LB --> BR
    BR --> DH
    BPE --> PEC
    BPE --> DH
    LF --> CC
```

## 3. Sequence — monthly run with alerts firing

```mermaid
sequenceDiagram
    autonumber
    participant U as Owner / Scheduler
    participant L as load_facts
    participant B as build_report
    participant P as build_per_entity_report
    participant W as writers
    participant R as render_html

    U->>L: load_facts("data")
    L-->>U: (180 facts, 0 unmapped)
    U->>B: build_report(facts, budget, variance_threshold=10)
    B->>B: per category: a=YTD actual, b=YTD budget, var_pct = (a-b)/b·100
    B->>B: if abs(var_pct) > threshold → flagged=true, alerts.append(...)
    B-->>U: {rows: [{...flagged:true}...], summary: {alerts:[...]}}
    U->>P: build_per_entity_report(facts)
    P-->>U: {(entity, category): YTD_amount}
    U->>W: write each CSV
    U->>R: render_html(report, per_entity, unmapped)
    R-->>U: dashboard.html with KPI cards + alert banner + per-entity matrix
```

## 4. Identity — per-entity sums must equal consolidated rows

```mermaid
flowchart TB
    PE["build_per_entity_report(facts)"] --> M["{(entity, category): amount}"]
    M --> GB["group by category, sum"]
    R["build_report(facts, budget)"] --> RR["row['ytd_actual'] per category"]

    GB -.->|"MUST equal"| RR
    GB --> EVAL["evals/golden.json:<br/>per_entity_sums_match_consolidated"]
    RR --> EVAL
    EVAL --> CI["CI gate"]
```

This identity is the canary — it catches drift if the aggregation logic
ever changes inconsistently between the two functions. The eval case
asserts equality (rounded to 2 dp) for every category in the consolidated
rows.
