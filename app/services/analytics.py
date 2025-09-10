from typing import Dict, Any, List

DEFAULT_WEIGHTS = {
    "net_yield": 0.25,
    "cagr5": 0.20,
    "vacancy_inverse": 0.10,
    "cash_on_cash": 0.10,
    "value_add": 0.10,
    "amenities": 0.10,
    "affordability": 0.05,
    "risk_inverse": 0.10,
}

def _safe_float(v, default=None):
    try:
        return float(v)
    except Exception:
        return default

def _normalize_0_1(value, min_val, max_val):
    if value is None or max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

def _risk_to_score(flood_risk: str|None, bushfire_risk: str|None, crime_band: str|None) -> float:
    m = {"none": 0, "low": 0.25, "medium": 0.5, "high": 1.0}
    flood = m.get((flood_risk or "none").lower(), 0.5)
    bush = m.get((bushfire_risk or "none").lower(), 0.5)
    crime_map = {"low": 0.1, "medium": 0.5, "high": 1.0}
    crime = crime_map.get((crime_band or "medium").lower(), 0.5)
    return (flood + bush + crime) / 3.0  # higher = riskier

def _value_add_score(row: Dict[str, Any]) -> float:
    land = _safe_float(row.get("land_m2"), 0) or 0
    frontage = _safe_float(row.get("frontage_m"), 0) or 0
    gf = bool(row.get("granny_flat_allowed"))
    dual = bool(row.get("dual_occ_allowed"))
    score = 0.0
    if gf and land >= 450: score += 0.6
    if dual and frontage >= 12.5 and land >= 550: score += 0.4
    return min(score, 1.0)

def _amenities_score(row: Dict[str, Any]) -> float:
    s = _safe_float(row.get("amenities_score"), 0.5)
    return max(0.0, min(1.0, s if s is not None else 0.5))

def _affordability(row: Dict[str, Any]) -> float:
    price = _safe_float(row.get("list_price"), None)
    beds = _safe_float(row.get("beds"), 3) or 3
    if not price or price <= 0: return 0.5
    price_per_bed = price / max(beds, 1)
    return 1.0 - _normalize_0_1(price_per_bed, 120_000, 350_000)

def _cash_on_cash(row: Dict[str, Any]) -> float:
    price = _safe_float(row.get("list_price"), None)
    rent_w = _safe_float(row.get("weekly_rent"), None)
    if not price or not rent_w: return 0.0
    annual_rent = rent_w * 52
    expenses = 0.25 * annual_rent
    interest = 0.065 * (0.80 * price)
    noi = annual_rent - expenses - interest
    equity = 0.20 * price
    return 0.0 if equity <= 0 else (noi / equity)

def _gross_yield(row: Dict[str, Any]) -> float|None:
    price = _safe_float(row.get("list_price"), None)
    rent_w = _safe_float(row.get("weekly_rent"), None)
    return ((rent_w * 52) / price) if price and rent_w and price > 0 else None

def _net_yield(row: Dict[str, Any]) -> float|None:
    gy = _gross_yield(row)
    return gy * 0.75 if gy is not None else None  # 25% expense assumption

def compute_analytics_for_one(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    gy = _gross_yield(row)
    ny = _net_yield(row)
    cagr5 = _safe_float(row.get("cagr5"), None)
    vac = _safe_float(row.get("vacancy"), None)
    risk = _risk_to_score(row.get("flood_risk"), row.get("bushfire_risk"), row.get("crime_band"))
    vall = _value_add_score(row)
    coc = _cash_on_cash(row)
    aff = _affordability(row)
    amen = _amenities_score(row)

    ny_n = _normalize_0_1(ny, 0.01, 0.08)
    cagr_n = _normalize_0_1(cagr5, 0.0, 0.10)
    vac_inv = 1.0 - _normalize_0_1(vac, 0.5, 5.0)
    coc_n = _normalize_0_1(coc, 0.0, 0.15)
    aff_n = aff
    risk_inv = 1.0 - risk

    w = DEFAULT_WEIGHTS
    contrib = {
        "net_yield": w["net_yield"] * ny_n,
        "cagr5": w["cagr5"] * cagr_n,
        "vacancy_inverse": w["vacancy_inverse"] * vac_inv,
        "cash_on_cash": w["cash_on_cash"] * coc_n,
        "value_add": w["value_add"] * vall,
        "amenities": w["amenities"] * amen,
        "affordability": w["affordability"] * aff_n,
        "risk_inverse": w["risk_inverse"] * risk_inv,
    }
    deal_score = sum(contrib.values())

    out.update({
        "gross_yield": gy,
        "net_yield": ny,
        "cagr5": cagr5,
        "vacancy": vac,
        "risk_score": risk,
        "value_add_score": vall,
        "cash_on_cash": coc,
        "affordability": aff_n,
        "deal_score": deal_score,
        "score_breakdown": contrib,
    })
    return out

def compute_analytics_for_all(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [compute_analytics_for_one(r) for r in rows]

def filters_apply(rows: List[Dict[str, Any]],
                  min_gross_yield: float | None = None,
                  min_net_yield: float | None = None,
                  min_cagr5: float | None = None,
                  max_vacancy: float | None = None,
                  exclude_flood_high: bool = True,
                  exclude_bushfire_high: bool = True) -> List[Dict[str, Any]]:
    def ok(r):
        if min_gross_yield is not None and (r.get("gross_yield") or 0) < min_gross_yield: return False
        if min_net_yield  is not None and (r.get("net_yield")  or 0) < min_net_yield:  return False
        if min_cagr5      is not None and (r.get("cagr5")      or 0) < min_cagr5:      return False
        if max_vacancy    is not None and (r.get("vacancy")    or 0) > max_vacancy:    return False
        if exclude_flood_high and str(r.get("flood_risk","")).lower() == "high":       return False
        if exclude_bushfire_high and str(r.get("bushfire_risk","")).lower() == "high": return False
        return True
    return [r for r in rows if ok(r)]

def sort_properties(rows: List[Dict[str, Any]], sort_by: str = "deal_score", sort_dir: str = "desc") -> List[Dict[str, Any]]:
    reverse = sort_dir.lower() == "desc"
    return sorted(rows, key=lambda r: (r.get(sort_by) is None, r.get(sort_by, 0)), reverse=reverse)
