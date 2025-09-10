import csv, os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime
SALES_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nsw_sales.csv")
def parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            pass
    return None
def load_sales_by_suburb() -> List[dict]:
    if not os.path.exists(SALES_CSV):
        return []
    rows = []
    with open(SALES_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows
def compute_median_price_by_suburb_years(years: int = 5) -> Dict[Tuple[str, str], float]:
    from statistics import median
    sales = load_sales_by_suburb()
    if not sales:
        return {}
    cutoff = datetime.utcnow().year - years
    bucket: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    for s in sales:
        suburb = (s.get("suburb") or s.get("SUBURB") or "").upper()
        pc = (s.get("postcode") or s.get("POSTCODE") or "")
        price_raw = s.get("price") or s.get("PRICE")
        date_raw = s.get("contract_date") or s.get("CONTRACT_DATE") or s.get("SETTLEMENT_DATE") or ""
        dt = parse_date(date_raw)
        try:
            price = float(str(price_raw).replace(",", "").replace("$", ""))
        except Exception:
            continue
        if dt and dt.year >= cutoff:
            bucket[(suburb, pc)].append(price)
    out = {}
    for k, vals in bucket.items():
        if vals:
            out[k] = median(vals)
    return out