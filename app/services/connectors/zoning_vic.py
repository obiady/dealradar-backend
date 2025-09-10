import httpx
from typing import Optional, Tuple

TIMEOUT = 15.0
VICMAP_FS = "https://services6.arcgis.com/GB33F62SbDxJjwEL/arcgis/rest/services/Vicmap_Planning/FeatureServer"
PLAN_ZONE_LAYER = 3
BPA_LAYER = 9

def _query_point(layer_url: str, x: float, y: float, wkid: int = 4326):
    params = {
        "f": "json",
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR": wkid,
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "false",
        "outFields": "*",
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(layer_url + "/query", params=params)
        r.raise_for_status()
        return r.json()

def vic_get_zone_bpa(lat: float, lng: float) -> Tuple[Optional[str], Optional[bool]]:
    x, y = (lng, lat)
    zone_code = None
    is_bpa = None
    try:
        js = _query_point(f"{VICMAP_FS}/{PLAN_ZONE_LAYER}", x, y)
        feats = js.get("features") or []
        if feats:
            attrs = feats[0].get("attributes") or {}
            zone_code = (attrs.get("ZONE_CODE") or attrs.get("ZONE") or attrs.get("ZONING") or attrs.get("MAINZONE") or "").strip() or None
    except Exception:
        pass
    try:
        js = _query_point(f"{VICMAP_FS}/{BPA_LAYER}", x, y)
        feats = js.get("features") or []
        is_bpa = bool(feats)
    except Exception:
        pass
    return zone_code, is_bpa
