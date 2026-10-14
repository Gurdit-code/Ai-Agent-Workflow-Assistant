from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"


def read_rows(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return pd.read_csv(path).fillna("").to_dict("records")


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0
