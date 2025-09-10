import pandas as pd
import os
from typing import Dict, Any, List, Optional
BASE_DIR = os.path.dirname(__file__)
DATA_CSV = os.path.join(BASE_DIR, "data", "sample_listings.csv")
ENRICHED_CSV = os.path.join(BASE_DIR, "data", "enriched_listings.csv")
def _load_csv(path: str) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    df["id"] = df["id"].astype(str)
    bool_cols = ["granny_flat_allowed","dual_occ_allowed","heritage_flag"]
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].astype(bool)
    for c in ["zoning_code","dwelling_type","address","suburb","state","postcode"]:
        if c in df.columns:
            df[c] = df[c].fillna("")
    return df.to_dict(orient="records")
def _load() -> List[Dict[str, Any]]:
    path = ENRICHED_CSV if os.path.exists(ENRICHED_CSV) else DATA_CSV
    return _load_csv(path)
DATASET = _load()
def get_property_by_id(prop_id: str) -> Optional[Dict[str, Any]]:
    for row in DATASET:
        if str(row.get("id")) == str(prop_id):
            return dict(row)
    return None