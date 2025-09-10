import csv, os
from typing import Dict, Optional
CRIME_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "bocsar_suburb_crime.csv")
def load_crime_band(suburb: str, state: str) -> Optional[str]:
    if not os.path.exists(CRIME_CSV):
        return None
    ss = suburb.upper().strip()
    st = state.upper().strip()
    with open(CRIME_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("suburb","").upper().strip() == ss and
                row.get("state","").upper().strip() == st):
                return (row.get("crime_band") or "").lower() or None
    return None