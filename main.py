from pathlib import Path

import pandas as pd
from registry import WORKFLOW_IDS

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
BOOK = DATA_DIR / "workflows.xlsx"


def load_workflows():
    book = BOOK
    if not book.exists():
        files = list(DATA_DIR.glob("*.xlsx")) if DATA_DIR.exists() else []
        if not files:
            raise FileNotFoundError(f"Excel workbook not found: {BOOK}")
        book = files[0]

    flows = pd.read_excel(book, sheet_name="Workflows")
    required = {"Workflow_ID", "Workflow_Name", "Steps"}
    missing = required - set(flows.columns)
    if missing:
        raise ValueError(f"Excel is missing required columns: {sorted(missing)}")
    flows["Workflow_ID"] = flows["Workflow_ID"].astype(str).str.strip()
    return flows[flows["Workflow_ID"].isin(WORKFLOW_IDS)].copy()
