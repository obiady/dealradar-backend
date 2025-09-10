import httpx
from typing import Optional
BFPL_MAPSERVER = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer"
def get_bushfire_category(lat: float, lng: float, timeout: float = 8.0) -> Optional[str]:
    layer_ids = ["0", "1", "2", "229"]
    for lid in layer_ids:
        try:
            val = _query_layer(BFPL_MAPSERVER, lid, lat, lng, timeout)
            if val:
                return val
        except Exception:
            continue
    return None
def _query_layer(base, layer_id, lat, lng, timeout):
    params = {
        "f": "json",
        "geometry": json_dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    }
    url = f"{base}/{layer_id}/query"
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        feats = data.get("features", [])
        if not feats:
            return None
        attrs = feats[0].get("attributes", {}) or {}
        for k in ("CATEGORY", "Category", "VEG_CATEGORY", "BFPL_CATEGORY", "BUSHFIREPRONE"):
            if k in attrs and attrs[k]:
                return str(attrs[k])
        for k, v in attrs.items():
            if isinstance(v, str) and ("Category" in k or "BF" in k.upper()):
                return v
    return None
def json_dumps(o):
    import json
    return json.dumps(o, separators=(",", ":"))