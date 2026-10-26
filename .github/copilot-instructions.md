# Copilot instructions: Financial Sector Risk Intelligence Model

## Purpose
Public-source financial-sector risk intelligence framework with live data layers, scenario analysis, Monte Carlo robustness testing, PDF reporting, and an interactive dashboard.

## Tech stack
- Python; dependencies in `requirements.txt`
- Key libraries: `pandas`, `numpy`, `matplotlib`, `reportlab`, `streamlit`, `plotly`, `requests`, `yfinance`, `python-dotenv`

## Folder structure
- `assets/` (5 files)
- `src/` (14 files)
- `README.md`
- `app.py`
- `main.py`
- `requirements.txt`

## Setup, run, test
Commands documented in README.md (referenced files exist):
```bash
python -m venv .venv
pip install -r requirements.txt
```
- Run offline regression tests with `python -m pytest -q` (install `requirements-dev.txt`); add tests under `tests/`.

## Conventions observed
- Functions use type hints; keep annotating new code.
- Uses `dataclasses` for structured config/results.
- Config lives in: `src/config.py`; avoid hardcoding parameters elsewhere.
- Random seeds are set for reproducibility (Monte Carlo/simulation); keep seeded, deterministic runs.
- API keys are loaded from a local `.env` via python-dotenv; `.env` must stay uncommitted.
- Raw data (`data/raw/`) is gitignored; download/fetch it via the pipeline, do not commit it.
- Public data sources referenced: ACLED, yfinance, World Bank, OFAC, FATF, GDELT.
- Write paths relative to the repo root (no absolute local paths).

## Output artifacts
- A PDF report is produced with `reportlab`; keep it in sync with model changes.
- Streamlit dashboard: `app.py` (run with `streamlit run <file>`).
- Charts are generated with matplotlib / plotly.

## Guardrails
- Never commit secrets, API keys, tokens, or `.env` files.
- Do not commit large raw datasets or binaries; keep data fetched or documented with its source.
- Keep analysis source-backed: cite data sources and assumptions; label scenario/forecast outputs as model estimates, not facts.
- Preserve reproducibility: no unseeded randomness, no hidden manual steps.
