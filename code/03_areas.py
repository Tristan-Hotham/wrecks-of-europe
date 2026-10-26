"""Step 3: choose one position per entry, keep the ones in European seas, and give each a sea area.

Position (first rule that applies):
  a. coordinates given in the list ({{coord}}), unless they lie more than 10 km inland AND more
     than 250 km from the place the text names (a sign slip such as W for E): then the named place;
  b. the Wikidata wreck position of the ship's own article, if it is within 150 km of the named
     place, or if the text names no place;
  c. the first specific place linked in the loss text (02_locate.py).

European seas: 30 to 72 N and 25 W to 42 E, without the Atlantic south of 36 N (Morocco, Madeira,
Canaries) and without the Caspian; and not more than 50 km inland from the Natural Earth
coastline (river ports such as London, Hamburg and Rouen stay in), and not on a lake.

Sea area: the nearest Natural Earth 1:10m marine polygon (public domain), grouped into ten areas
(SEA_GROUP below). The sea named in the description, where there is one, is kept as a check.

Far offshore: if the text places the loss more than 60 nautical miles from the named place and
the list gives no coordinates, the entry is not placed (the named place is only a reference).

Coast: the modern country (Natural Earth 1:50m) nearest to the position.

Inputs : work/located.csv.gz, Natural Earth admin 0 countries 1:50m (path as argument)
Outputs: work/europe.csv.gz (all European entries, full columns)
         data/europe_countries_ne50m.geojson (the clipped Natural Earth layer used here)
"""
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape, box, Point, mapping
from shapely.ops import unary_union
import shapely
from shapely import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
NE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/sw/ne/geojson/ne_50m_admin_0_countries.geojson"
BOX = (-32, 26, 50, 76)
SEAS = ["North Sea", "English Channel", "Irish Sea and approaches", "Atlantic", "Bay of Biscay", "Kattegat and Skagerrak",
        "Baltic", "Norwegian Sea and Arctic", "Mediterranean", "Black Sea"]

SEA_GROUP = {
    "North Sea": "North Sea", "Waddenzee": "North Sea", "Boknafjorden": "North Sea",
    "English Channel": "English Channel",
    "Irish Sea": "Irish Sea and approaches", "Bristol Channel": "Irish Sea and approaches",
    "Inner Seas": "Irish Sea and approaches",
    "North Atlantic Ocean": "Atlantic", "Denmark Strait": "Atlantic",
    "Bay of Biscay": "Bay of Biscay",
    "Kattegat": "Kattegat and Skagerrak", "Skagerrak": "Kattegat and Skagerrak",
    "Baltic Sea": "Baltic", "Gulf of Finland": "Baltic", "Gulf of Bothnia": "Baltic", "Gulf of Riga": "Baltic",
    "Øresund": "Baltic", "Danish Belts (unnamed in Natural Earth)": "Baltic", "Mecklenburger Bucht": "Baltic", "Stettiner Haff": "Baltic", "Kaliningrad": "Baltic",
    "Norwegian Sea": "Norwegian Sea and Arctic", "Greenland Sea": "Norwegian Sea and Arctic", "Barents Sea": "Norwegian Sea and Arctic",
    "White Sea": "Norwegian Sea and Arctic", "Vestfjorden": "Norwegian Sea and Arctic", "Sognefjorden": "Norwegian Sea and Arctic",
    "Trondheimsfjorden": "Norwegian Sea and Arctic",
    "Mediterranean Sea": "Mediterranean", "Tyrrhenian Sea": "Mediterranean", "Adriatic Sea": "Mediterranean",
    "Ionian Sea": "Mediterranean", "Aegean Sea": "Mediterranean", "Balearic Sea": "Mediterranean", "Ligurian Sea": "Mediterranean",
    "Alboran Sea": "Mediterranean", "Golfe du Lion": "Mediterranean", "Sea of Crete": "Mediterranean", "Gulf of Gabès": "Mediterranean",
    "Gulf of Sidra": "Mediterranean", "Strait of Gibraltar": "Mediterranean", "Dardanelles": "Mediterranean",
    "Black Sea": "Black Sea", "Sea of Azov": "Black Sea", "Sea of Marmara": "Black Sea", "Bosporus": "Black Sea",
}
MARINE = os.path.join(os.path.dirname(NE), "..", "..", "..", "wo_gh", "nev", "geojson", "ne_10m_geography_marine_polys.geojson")
MARINE = sys.argv[2] if len(sys.argv) > 2 else MARINE

T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)


def proj(g):
    return shapely.transform(g, lambda a: np.column_stack(T.transform(a[:, 0], a[:, 1])))


def km(a, b, c, d):
    p = np.pi / 180
    h = np.sin((c - a) * p / 2) ** 2 + np.cos(a * p) * np.cos(c * p) * np.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))


def in_box(lat, lon):
    ok = (lat >= 30) & (lat <= 72) & (lon >= -25) & (lon <= 42)
    ok &= ~((lat < 36) & (lon < -5.6))          # Atlantic Morocco, Madeira, Canaries
    ok &= ~((lat < 31) & (lon > 31.5))          # Suez Canal and its lakes
    return ok


def main():
    gj = json.load(open(NE))
    clip = box(*BOX)
    feats, names, geoms = [], [], []
    for f in gj["features"]:
        g = shape(f["geometry"])
        if not g.intersects(clip):
            continue
        g = g.intersection(clip).simplify(0.01)
        nm = f["properties"]["ADMIN"]
        feats.append({"type": "Feature", "properties": {"name": nm}, "geometry": mapping(g)})
        names.append(nm)
        geoms.append(proj(g))
    json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(ROOT, "data", "europe_countries_ne50m.geojson"), "w"),
              separators=(",", ":"))
    land = unary_union(geoms)
    tree = STRtree(geoms)

    d = pd.read_csv(os.path.join(ROOT, "work", "located.csv.gz"), keep_default_na=False, low_memory=False)
    for c in ["link_lat", "link_lon", "coord_lat", "coord_lon", "wd_lat", "wd_lon", "offset_nmi"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n = len(d)
    lat = np.full(n, np.nan); lon = np.full(n, np.nan); method = np.array([""] * n, dtype=object)
    hasL = d.link_lat.notna().values; hasC = d.coord_lat.notna().values; hasW = d.wd_lat.notna().values
    dLC = km(d.coord_lat.values, d.coord_lon.values, d.link_lat.values, d.link_lon.values)
    dLW = km(d.wd_lat.values, d.wd_lon.values, d.link_lat.values, d.link_lon.values)
    # inland depth of the list coordinates, only needed where they disagree with the named place
    coord_inland = np.zeros(n)
    for i in np.where(hasC & hasL & (dLC > 250))[0]:
        p = Point(*T.transform(d.coord_lon.iat[i], d.coord_lat.iat[i]))
        coord_inland[i] = land.boundary.distance(p) / 1000 if land.contains(p) else 0
    for i in range(n):
        if hasC[i] and not (hasL[i] and dLC[i] > 250 and coord_inland[i] > 10):
            lat[i], lon[i], method[i] = d.coord_lat.iat[i], d.coord_lon.iat[i], "list coordinates"
        elif hasW[i] and (not hasL[i] or dLW[i] <= 150):
            lat[i], lon[i], method[i] = d.wd_lat.iat[i], d.wd_lon.iat[i], "Wikidata wreck position"
        elif hasL[i]:
            lat[i], lon[i], method[i] = d.link_lat.iat[i], d.link_lon.iat[i], "named place"
    d["lat"], d["lon"], d["method"] = lat, lon, method
    d["coord_slip"] = (hasC & hasL & (dLC > 250) & (coord_inland > 10)).astype(int)
    d["wd_km_from_text"] = np.where(hasW & hasL, np.round(dLW, 1), np.nan)
    d["coord_km_from_text"] = np.where(hasC & hasL, np.round(dLC, 1), np.nan)

    eu = d[in_box(d.lat, d.lon) & d.lat.notna()].copy()
    xy = np.array([T.transform(lo, la) for la, lo in zip(eu.lat, eu.lon)])
    pts = [Point(x, y) for x, y in xy]
    inland = np.array([land.boundary.distance(p) / 1000 if land.contains(p) else 0.0 for p in pts])
    eu["inland_km"] = np.round(inland, 1)
    near = tree.nearest(pts)
    eu["coast"] = [names[k] for k in near]
    eu["coast_km"] = np.round([geoms[k].distance(p) / 1000 for k, p in zip(near, pts)], 1)
    lake = eu.place.str.contains(r"^(?:Lake |Loch )|Windermere|Mälaren|Lake Peipus", regex=True).values
    keep = (inland <= 50) & ~lake
    dropped_inland = int((~keep).sum())
    eu, xy = eu[keep].copy(), xy[keep]
    # far offshore: the named place is only a reference point
    far = ((eu.method == "named place") & (eu.offset_nmi > 60)).values
    dropped_far = int(far.sum())
    eu, xy = eu[~far].copy(), xy[~far]
    # sea area: nearest Natural Earth marine polygon
    mg = json.load(open(MARINE))
    mfe, mge = [], []
    for f in mg["features"]:
        g = shape(f["geometry"])
        nm = f["properties"]["name"]
        if nm is None:
            b = g.bounds   # the unnamed polygon covering the Danish Belts
            nm = "Danish Belts (unnamed in Natural Earth)" if (b[0] > 9 and b[2] < 12.5 and b[1] > 54 and b[3] < 57) else "x"
        if not g.intersects(clip) or nm not in SEA_GROUP:
            continue
        g = g.intersection(clip).simplify(0.01)
        mfe.append({"type": "Feature", "properties": {"name": nm, "area": SEA_GROUP[nm]}, "geometry": mapping(g)})
        mge.append(proj(g))
    json.dump({"type": "FeatureCollection", "features": mfe}, open(os.path.join(ROOT, "data", "sea_areas_ne10m.geojson"), "w"),
              separators=(",", ":"))
    mtree = STRtree(mge)
    uniq = {}
    for k, (x, y) in enumerate(xy):
        uniq.setdefault((round(x), round(y)), []).append(k)
    sea_poly = np.empty(len(eu), dtype=object)
    for (x, y), ks in uniq.items():
        j = mtree.nearest(Point(x, y))
        nm = mfe[j]["properties"]["name"]
        for k in ks:
            sea_poly[k] = nm
    eu["sea_polygon"] = sea_poly
    eu["sea"] = [SEA_GROUP[n] for n in sea_poly]
    eu.to_csv(os.path.join(ROOT, "work", "europe.csv.gz"), index=False, compression="gzip")
    d.to_csv(os.path.join(ROOT, "work", "located_final.csv.gz"), index=False, compression="gzip")
    stats = {"entries": n, "with_position": int(d.lat.notna().sum()), "in_box": int(in_box(d.lat, d.lon).sum()),
             "dropped_inland_or_lake": dropped_inland, "dropped_far_offshore": dropped_far, "europe": len(eu), "coord_slips": int(d.coord_slip.sum())}
    json.dump(stats, open(os.path.join(ROOT, "work", "areas_stats.json"), "w"), indent=1)
    print(stats)
    print(eu.method.value_counts())
    print(eu.sea.value_counts())
    print(eu.coast.value_counts().head(20))


if __name__ == "__main__":
    main()
