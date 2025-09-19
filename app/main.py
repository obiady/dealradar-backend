from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from .services.connectors.nestoria import (
    search_listings as nestoria_search,
    normalize as nestoria_normalize,
)
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
    limit: int = Query(12, ge=1, le=100),
    sort_by: str = Query("deal_score"),
    sort_dir: str = Query("desc"),
    min_gross_yield: float | None = None,
    min_net_yield: float | None = None,
    min_cagr5: float | None = None,
    max_vacancy: float | None = None,
    exclude_flood_high: bool = True,
    exclude_bushfire_high: bool = True,
    suburb: str | None = None,
    state: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    use_nestoria: bool = True,
):
    base = DATASET if isinstance(DATASET, list) else DATASET.to_dict(orient="records")
    rows = list(base)

    # optionally fetch Nestoria AU listings
    if use_nestoria:
        place = suburb if suburb else None
        if state and place:
            place = f"{place}, {state}"
        try:
            listings, _meta = nestoria_search(
                place=place,
                min_price=min_price,
                max_price=max_price,
                listing_type="buy",
                page=1,
                per_page=50,
            )
            rows += [nestoria_normalize(li) for li in listings]
        except Exception as e:
            print("Nestoria error:", e)

    # analytics + filters + sort
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
    debug: bool = False,
):
    # DATASET is a list of dicts (from dataset.py); keep fallback if someone reverts it
    rows: List[Dict[str, Any]] = DATASET if isinstance(DATASET, list) else DATASET.to_dict(orient="records")

    # Quick debug: show dataset size and first record without running analytics
    if debug:
        summary = {
            "dataset_len": len(rows),
            "first_row_keys": list(rows[0].keys()) if rows else [],
            "first_row_sample": rows[0] if rows else None,
        }
        return JSONResponse(content=jsonable_encoder(summary))

    try:
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
    except Exception as e:
        # Return error details to the client to avoid blind guessing
        return JSONResponse(
            status_code=500,
            content={
                "code": "properties_failed",
                "message": "Failed to compute/serialize properties.",
                "detail": str(e),
            },
        )

@app.get("/property/{pid}")
def property_by_id(pid: str):
    row = get_property_by_id(pid)
    if not row:
        return JSONResponse(status_code=404, content={"error": "not found"})
    row = compute_analytics_for_all([row])[0]
    return JSONResponse(content=jsonable_encoder(row))
