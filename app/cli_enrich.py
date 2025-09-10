import os, pandas as pd

# Look in both data locations we’ve been using
BASE_DIR = os.path.dirname(__file__)
DATA_DIRS = [
    os.path.join(BASE_DIR, "services", "data"),
    os.path.join(BASE_DIR, "data"),
]

from .services.connectors.flood_qld import qld_get_flood_risk
from .services.connectors.zoning_vic import vic_get_zone_bpa

def _find_input_csv():
    for d in DATA_DIRS:
        p = os.path.join(d, "enriched_listings.csv")
        if os.path.exists(p): return p, d
    for d in DATA_DIRS:
        p = os.path.join(d, "sample_listings.csv")
        if os.path.exists(p): return p, d
    raise FileNotFoundError("No sample_listings.csv or enriched_listings.csv found under data dirs")

def main():
    in_path, base_dir = _find_input_csv()
    print(f"Loading: {in_path}")
    df = pd.read_csv(in_path)

    for col in ["flood_risk","bushfire_risk","zoning_code"]:
        if col not in df.columns: df[col] = None

    rows = df.to_dict(orient="records")
    out = []
    for r in rows:
        state = str(r.get("state","")).upper()
        lat, lng = r.get("lat"), r.get("lng")
        if lat is None or lng is None:
            out.append(r); continue

        if state == "QLD":
            fr = qld_get_flood_risk(lat, lng)
            if fr: r["flood_risk"] = fr

        if state == "VIC":
            z, bpa = vic_get_zone_bpa(lat, lng)
            if z: r["zoning_code"] = z
            if bpa is not None:
                r["bushfire_risk"] = "high" if bpa else (r.get("bushfire_risk") or "none")

        out.append(r)

    out_df = pd.DataFrame(out)
    out_path = os.path.join(base_dir, "enriched_listings.csv")
    out_df.to_csv(out_path, index=False)
    print(f"Saved enriched CSV -> {out_path}")

if __name__ == "__main__":
    main()
