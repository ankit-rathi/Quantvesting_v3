# Quantvesting — Phase B

Phase B turns the Phase-A notebook engine into a **reproducible, multi-portfolio, PostgreSQL-ready analysis engine** while keeping CSV + Jupyter as the current storage/UI implementation.

## Implemented

### 1. Canonical data model
- Shared market data remains under `market_data/`.
- User portfolio data remains under `portfolio_data/<portfolio_id>/`.
- Security-level datasets are validated as one-row-per-symbol.
- Holding-level portfolio rows may still contain multiple account records (DM/SV/etc.).

### 2. Portfolio identity
Every portfolio run carries a `portfolio_id`, inferred from the portfolio folder when not explicitly supplied.

### 3. Run identity
Every analysis execution carries a unique `run_id`. A single end-to-end notebook execution can use the same run ID for both prospect and portfolio analysis.

### 4. Strategy version
The strategy version is read from `config/strategy.yaml` and recorded with each run. The current strategy remains `0.4`; Phase B does not change the investment methodology.

### 5. Run manifest / historical run tracking
`portfolio_data/<portfolio_id>/myRuns.csv` records execution metadata including:

- run ID
- portfolio ID
- analysis type
- run timestamp
- strategy version
- engine version
- configuration hash
- input data fingerprints
- EOD flag
- status
- reproducibility hash

### 6. Validation
Structural validation runs before analysis and checks required columns, non-empty inputs, security-level uniqueness, numeric fields and basic holding constraints.

### 7. Reproducibility
Each run records deterministic SHA-256 fingerprints for the relevant market/portfolio inputs and configuration. The combined `reproducibility_hash` provides a compact identity for the strategy/input combination.

### 8. EOD snapshot fix
`myPortfolioDB.csv` now:

- uses canonical `DD-MM-YYYY` dates
- parses legacy mixed date formats before comparison
- replaces all existing rows for the same calendar day on an EOD upsert
- sorts the complete history chronologically
- retains the existing snapshot metrics
- populates legacy/API aliases (`investment` + `initial_investment`/`deployed`, `cagr` + `cagr_xirr`) so old and new rows remain schema-compatible
- adds Phase-B metadata to new rows

This fixes the previous mismatch where `YYYY-MM-DD` and `DD-MM-YYYY` could represent the same day but were treated as different strings.

### 9. Screener refresh safety
`myScreenerDB.xlsx` remains authoritative for symbols present in the workbook. Their old CSV rows are removed and the latest XLSX rows are inserted. Persisted CSV duplicates are also cleaned during ingestion.

## Compatibility

The following remain unchanged:

- prospect ranking methodology and default equal weights
- portfolio calculations
- DM + SV aggregation behaviour
- `CumlRnk`, FTT, allocation and target calculations
- Jupyter/Colab workflow
- CSV as the current storage layer
- existing public `Quantvesting` interface
- optional `REFRESH_SCREENER` and `EOD_RUN` controls

## PostgreSQL readiness

The engine still depends on repository interfaces rather than direct CSV operations in the analysis layer:

```text
Jupyter / future API
        |
        v
Quantvesting facade
        |
        v
Engine + validation + run context
        |
        v
Repository interfaces
      /     \
     /       \
 CSV files  PostgreSQL (Phase C)
```

Phase C can therefore add `PostgresMarketDataRepository` / `PostgresPortfolioRepository` without changing the prospect, portfolio or decision calculations.

## Current Phase-B definition of done

- [x] Canonical portfolio/security data boundaries
- [x] `portfolio_id`
- [x] `run_id`
- [x] strategy version
- [x] run manifest
- [x] historical run tracking
- [x] input validation
- [x] reproducibility fingerprints
- [x] EOD upsert + chronological sorting fix
- [x] Screener refresh replacement/deduplication
- [x] existing notebook compatibility
- [x] CSV repository implementation
- [x] PostgreSQL-ready repository boundary

## Next: Phase C

1. PostgreSQL repository implementation
2. FastAPI service layer
3. Web UI
4. Preserve the same engine contracts and run metadata

## Strategy refinement (v0.5)

Phase B now preserves the full 12-level conviction priority map while making the current six-bucket preference explicit.

### Conviction hierarchy

The exact priority order remains:

```text
X-LC, H-LC, X-MC, X-SC, M-LC, H-MC, H-SC, L-LC, M-MC, M-SC, L-MC, L-SC
```

The first six are `CORE` and receive new-opportunity `CumlRnk`. The remaining six are `LEGACY`; they remain visible and manageable but do not compete for new-capital ranking. This accommodates older portfolio positions without treating them as immediate sell candidates.

### Capital-rotation state

Portfolio analysis now derives `ThesisCaptured%`, `RemainingUpside%` and `RotationStatus`. The decision layer adds `REVIEW_ROTATION` as an advisory state, `WAIT_FOR_EXIT_WINDOW` for legacy positions, and `EXIT_TARGET` based on per-share CMP versus per-share FTT. A separate `capital_rotation_actions()` comparison can identify a better-ranked CORE prospect as a potential destination for released capital. No automatic SELL is generated by this comparison.

This keeps the investment philosophy explicit while preserving the existing `RRR Ind`, FTT and portfolio calculations.

## Data-quality validation policy

Shared market data is intentionally broader than the active Quantvesting
analysis universe. Therefore:

- populated non-numeric values in the active universe are validation errors;
- missing numeric market values (`NaN`) are treated as incomplete data, not
  malformed data;
- missing values and malformed populated values outside the active universe
  generate informational/warning messages and never stop the pipeline;
- duplicate symbols in the active universe remain errors because they can
  corrupt security-level calculations;
- duplicate symbols outside the active universe are warnings only;
- validation reports are attached to analysis results/portfolio summaries so
  Jupyter, API and future Web UI layers can present the same quality status.

A successful run may therefore have status `SUCCESS_WITH_WARNINGS` without
changing the investment calculations for the active universe.
