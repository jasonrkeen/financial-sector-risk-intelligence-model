from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = BASE_DIR / "outputs"
TABLES_DIR = OUTPUT_DIR / "tables"
CHARTS_DIR = OUTPUT_DIR / "charts"
REPORTS_DIR = OUTPUT_DIR / "reports"


def ensure_directories() -> None:
    """Create required project directories if they do not already exist."""
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        TABLES_DIR,
        CHARTS_DIR,
        REPORTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

# Stop incomplete or looping API downloads rather than score partial data.
ACLED_MAX_PAGES = 1000
