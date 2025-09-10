import httpx
from typing import Optional

TIMEOUT = 15.0

# Sunshine Coast FeatureServer: Flood Hazard Overlay polygons
SUNSHINE_FLOOD_FS = "https://services-ap1.arcgis.com/YQyt7djuXN7rQyg4/ArcGIS/rest/services/Flood_Hazard_Overlay_i_Flood_Risk_Area/FeatureServer/0"

# Gold Coast MapServer: V8 Overlays
GCCC_OVERLAYS_MS = "https://maps1.goldcoast.qld.gov.au/arcgis/rest/services/V8_Overlays/MapServer"
GCCC_FLOOD_LAYER = 79                 # Flood overlay
GCCC_FLOOD_ASSESS_LAYER = 80          # Flood assessment required

# QLD FloodCheck MapServer fallback (state)
FLOODCHECK_MS = "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/FloodCheck/RapidHazardAssessmentMapSeries/MapServer"

def _arcgis_point_query(url: str, x: float, y: float, wkid: int = 4326, out_fields: str = "*"):
    params = {
        "f": "json",
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR": wkid,
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "false",
        "outFields": out_fields,
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(url + "/query", params=params)
        r.raise_for_status()
        return r.json()

def _arcgis_identify_ms(url: str, layer_ids: list[int], x: float, y: float, wkid: int = 4326, tolerance: int = 3):
    params = {
        "f": "json",
        "geometry": f'{{"x":{x},"y":{y},"spatialReference":{{"wkid":{wkid}}}}}',
        "geometryType": "esriGeometryPoint",
        "sr": wkid,
        "tolerance": tolerance,
        "mapExtent": f"{x-0.01},{y-0.01},{x+0.01},{y+0.01}",
        "imageDisplay": "400,400,96",
        "layers": "all:" + ",".join(str(i) for i in layer_ids),
        "returnGeometry": "false",
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(url + "/identify", params=params)
        r.raise_for_status()
        return r.json()

def qld_get_flood_risk(lat: float, lng: float) -> Optional[str]:
    """Return 'high'|'medium'|'low'|'none'|'unknown' for a QLD coordinate."""
    x, y = (lng, lat)

    # 1) Sunshine Coast
    try:
        js = _arcgis_point_query(SUNSHINE_FLOOD_FS, x, y)
        feats = js.get("features") or []
        if feats:
            attrs = feats[0].get("attributes") or {}
            val = (attrs.get("RISK") or attrs.get("FLOOD_RISK") or attrs.get("FLOOD_RISK_AREA") or "").strip().lower()
            if "high" in val: return "high"
            if "moderate" in val or "medium" in val: return "medium"
            if "low" in val: return "low"
            return "medium"
    except Exception:
        pass

    # 2) Gold Coast overlays
    try:
        js = _arcgis_identify_ms(GCCC_OVERLAYS_MS, [GCCC_FLOOD_LAYER, GCCC_FLOOD_ASSESS_LAYER], x, y)
        results = js.get("results") or []
        if results:
            names = " ".join((r.get("layerName","") or "").lower() for r in results)
            if "flood assessment required" in names: return "medium"
            if "flood" in names: return "medium"
    except Exception:
        pass

    # 3) State fallback
    try:
        js = _arcgis_identify_ms(FLOODCHECK_MS, [0], x, y)
        results = js.get("results") or []
        return "medium" if results else "none"
    except Exception:
        return "unknown"
