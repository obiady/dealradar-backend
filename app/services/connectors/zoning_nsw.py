import httpx
from typing import Optional
ZONING_FEATURESERVER = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/EPI_Primary_Planning_Layers/FeatureServer/2"
def get_zoning(lat: float, lng: float, timeout: float = 8.0) -> Optional[str]:
    params = {
        "f": "json",
        "geometry": json_dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "ZONE",
        "returnGeometry": "false",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{ZONING_FEATURESERVER}/query", params=params)
            r.raise_for_status()
            data = r.json()
            feats = data.get("features", [])
            if not feats:
                return None
            attrs = feats[0].get("attributes", {}) or {}
            return attrs.get("ZONE") or attrs.get("Zone") or attrs.get("LAND_ZONE") or None
    except Exception:
        return None
def json_dumps(o):
    import json
    return json.dumps(o, separators=(",", ":"))