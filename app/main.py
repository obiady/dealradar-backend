from __future__ import annotations
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from .services.dataset import DATASET, get_property_by_id
from .services.analytics import (
    compute_analytics_for_all,
    filters_apply,
    sort_properties,
)

app = FastAPI(title="DealRadar AU API", version="0.2.0")

# Allow local dev & WP/Next front-ends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down later if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "endpoints": ["/health", "/properties", "/property/{id}", "/docs"]}

@app.head("/health")
def head_health():
    return Response(status_code=200)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/properties")
def list_properties(
    limit: int = Query(50, ge=1, le=500),
    min_gross_yield: Optional[float] = None,
    min_net_yield: Optional[float] = None,
    min_cagr5: Optional[float] = None,
    max_vacancy: Optional[float] = None,
    exclude_flood_high: bool = True,
    exclude_bushfire_high: bool = True,
    sort_by: str = "deal_score",
    sort_dir: str = "desc",
):
    # DATASET is now a list of dicts (from dataset.py)
    rows: List[Dict[str, Any]] = DATASET if isinstance(DATASET, list) else DATASET.to_dict(orient="records")
    rows = compute_analytics_for_all(rows)
    rows = filters_apply(
        rows,
        min_gross_yield=min_gross_yield,
        min_net_yield=min_net_yield,
        min_cagr5=min_cagr5,
        max_vacancy=max_vacancy,
        exclude_flood_high=exclude_flood_high,
        exclude_bushfire_high=exclude_bushfire_high,
    )
    rows = sort_properties(rows, sort_by=sort_by, sort_dir=sort_dir)
    return JSONResponse(content=jsonable_encoder(rows[:limit]))

@app.get("/property/{pid}")
def property_by_id(pid: str):
    row = get_property_by_id(pid)
    if not row:
        return JSONResponse(status_code=404, content={"error": "not found"})
    row = compute_analytics_for_all([row])[0]
    return JSONResponse(content=jsonable_encoder(row))
