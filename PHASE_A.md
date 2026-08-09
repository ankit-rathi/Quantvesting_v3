# Phase A implementation

Implemented on top of the supplied Quantvesting v3 repository.

## Added
- `src/quantvesting/ingestion.py`
  - Screener XLSX hyperlink extraction
  - XLSX -> canonical CSV conversion
  - preservation/merge of older CSV securities
  - LC/MC/SC reclassification
- `src/quantvesting/repositories.py`
  - market-data repository contract
  - portfolio repository contract
  - filesystem/CSV implementations
- `src/quantvesting/run_context.py`
  - IST timestamp helper
  - run_id generation
  - portfolio_id inference

## Updated
- `data.py`: loaders use repositories and expose portfolio_id.
- `portfolio.py`: portfolio_id/run_id awareness and real EOD persistence.
- `prospects.py`: run metadata via DataFrame attrs.
- `__init__.py`: public ingestion/repository/run APIs.
- `strategy.yaml`: configurable Screener ingestion.
- portfolio/master notebooks: Screener refresh and EOD controls.
- tests and requirements.
- README and portfolio template documentation.

## Compatibility
Existing notebook calls continue to work. EOD persistence is opt-in with
`eod=True`. Screener refresh is opt-in with `REFRESH_SCREENER=True`.
