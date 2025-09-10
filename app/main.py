from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import math
import numpy as np

from .services.dataset import DATASET, get_property_by_id
from .services.analytics import compute_analytics_for_all, filters_apply, sort_properties

app = FastAPI(title="DealRadar AU API", version="0.2.0")

# Allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _coerce(v):
    # Convert NumPy scalars to plain Python + scrub NaN/Inf
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        if math.isnan(f) or math.isinf(f): return None
        return f
    if isinstance(v, (np.bool_,)): return bool(v)
    return v

def _sanitize(rows):
    out = []
    for r in rows:
        nr = {}
        for k, v in r.items():
            if isinstance(v, dict):
                nr[k] = {kk: _coerce(vv) for kk, vv in v.items()}
            else:
                nr[k] = _coerce(v)
        out.append(nr)
    return out

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/properties")
def list_properties(
    min_gross_yield: float | None = Query(None),
    min_net_yield: float | None = Query(None),
    min_cagr5: float | None = Query(None),
    max_vacancy: float | None = Query(None),
    exclude_flood_high: bool = Query(True),
    exclude_bushfire_high: bool = Query(True),
    sort_by: str = Query("deal_score"),
    sort_dir: str = Query("desc"),
):
    rows = DATASET.to_dict(orient="records")
    rows = compute_analytics_for_all(rows)
    rows = filters_apply(rows, min_gross_yield, min_net_yield, min_cagr5, max_vacancy, exclude_flood_high, exclude_bushfire_high)
    rows = sort_properties(rows, sort_by, sort_dir)
    rows = _sanitize(rows)
    return {"count": len(rows), "items": rows}

@app.get("/properties/{pid}")
def get_property(pid: str):
    r = get_property_by_id(pid)
    if not r:
        return {}
    r = compute_analytics_for_all([r])[0]
    r = _sanitize([r])[0]
    return r
