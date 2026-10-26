"""Step 5: every number used on the page, in the paper, the blog and the collage -> data/results.json,
plus the reusable tables in data/ and the compact page data (data/page.json).

Run after 01 to 04.
"""
import json
import math
import os
import re
from collections import Counter

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D = os.path.join(ROOT, "data")
W = os.path.join(ROOT, "work")

SHOW = ["British", "German", "French", "Norwegian", "Dutch", "Italian", "Swedish", "Russian"]
COLOURS = {"British": "#2a78d6", "German": "#eb6834", "French": "#1baf7a", "Norwegian": "#eda100", "Dutch": "#e87ba4",
           "Italian": "#008300", "Swedish": "#6250d6", "Russian": "#e34948", "Other": "#8a8f98", "Unknown": "#c9ccd1"}
COLOURS_DARK = {"British": "#3987e5", "German": "#d95926", "French": "#199e70", "Norwegian": "#c98500", "Dutch": "#d55181",
                "Italian": "#008300", "Swedish": "#9085e9", "Russian": "#e66767", "Other": "#8a8f98", "Unknown": "#55595f"}
ERAS = [("1744 to 1792", 1744, 1792, "Age of sail"), ("1793 to 1815", 1793, 1815, "French wars"),
        ("1816 to 1859", 1816, 1859, "Peace and sail"), ("1860 to 1913", 1860, 1913, "Steam age"),
        ("1914 to 1918", 1914, 1918, "First World War"), ("1919 to 1938", 1919, 1938, "Between the wars"),
        ("1939 to 1945", 1939, 1945, "Second World War")]
SEAS = ["North Sea", "English Channel", "Irish Sea and approaches", "Atlantic", "Bay of Biscay", "Kattegat and Skagerrak",
        "Baltic", "Norwegian Sea and Arctic", "Mediterranean", "Black Sea"]
OWN = {"United Kingdom": "British", "Isle of Man": "British", "Jersey": "British", "Guernsey": "British", "France": "French",
       "Norway": "Norwegian", "Germany": "German", "Netherlands": "Dutch", "Denmark": "Danish", "Sweden": "Swedish",
       "Italy": "Italian", "Spain": "Spanish", "Portugal": "Portuguese", "Greece": "Greek", "Russia": "Russian",
       "Turkey": "Ottoman", "Belgium": "Belgian"}
COAST_GROUP = {"Isle of Man": "United Kingdom", "Jersey": "United Kingdom", "Guernsey": "United Kingdom"}


def disp(g):
    return g if g in SHOW or g == "Unknown" else "Other"


def era_of(y):
    for k, a, b, _ in ERAS:
        if a <= y <= b:
            return k
    return None


def shares(s, keys):
    n = len(s)
    c = Counter(s)
    return {k: round(c.get(k, 0) / n, 4) if n else 0 for k in keys}


def inv_simpson(s):
    c = Counter(x for x in s if x != "Unknown")
    n = sum(c.values())
    return round(1 / sum((v / n) ** 2 for v in c.values()), 2) if n else None


def main():
    allr = pd.read_csv(os.path.join(W, "located_final.csv.gz"), keep_default_na=False, low_memory=False)
    e = pd.read_csv(os.path.join(W, "europe.csv.gz"), keep_default_na=False, low_memory=False)
    stats = json.load(open(os.path.join(W, "areas_stats.json")))
    hc = json.load(open(os.path.join(W, "hand_check_summary.json")))
    for c in ["year", "naval"]:
        e[c] = e[c].astype(int)
    e["coast"] = e["coast"].replace(COAST_GROUP)
    e["fg"] = e["flag_group"].map(disp)
    e["era"] = e["year"].map(era_of)
    KEYS = SHOW + ["Other", "Unknown"]
    R = {}
    allr["year"] = allr["year"].astype(int)
    R["coverage"] = {
        "entries_parsed": len(allr), "year_first": int(allr.year.min()), "year_last": int(allr.year.max()),
        "pages": 1251, "pages_redirect": 49,
        "with_position_anywhere": stats["with_position"],
        "in_europe_box": stats["in_box"], "dropped_inland_or_lake": stats["dropped_inland_or_lake"],
        "dropped_far_offshore": stats["dropped_far_offshore"], "europe": len(e),
        "share_of_parsed_in_europe": round(len(e) / len(allr), 4),
        "method_named_place": int((e.method == "named place").sum()),
        "method_list_coordinates": int((e.method == "list coordinates").sum()),
        "method_wikidata": int((e.method == "Wikidata wreck position").sum()),
        "coord_slips_fixed": stats["coord_slips"],
        "no_position": int(pd.to_numeric(allr.lat, errors="coerce").isna().sum()),
        "sea_named_but_no_position": int((pd.to_numeric(allr.lat, errors="coerce").isna() & allr.sea_named.isin(SEAS)).sum()),
        "unknown_flag_europe": int((e.flag_group == "Unknown").sum()),
        "naval_europe": int(e.naval.sum()),
    }
    # validation
    named = e[e.sea_named != ""]
    wd = pd.to_numeric(e.wd_km_from_text, errors="coerce").dropna()
    cd = pd.to_numeric(e.coord_km_from_text, errors="coerce").dropna()
    R["checks"] = {"hand": hc, "named_sea_n": len(named), "named_sea_agree": round(float((named.sea_named == named.sea).mean()), 4),
                   "wikidata_pairs": int(len(wd)), "wikidata_median_km": round(float(wd.median()), 1),
                   "wikidata_within_50km": round(float((wd <= 50).mean()), 3),
                   "coord_pairs": int(len(cd)), "coord_median_km": round(float(cd.median()), 1),
                   "coord_within_50km": round(float((cd <= 50).mean()), 3),
                   "coord_pairs_pre1914": int((e.loc[cd.index, "year"] < 1914).sum()),
                   "coord_median_km_pre1914": round(float(cd[e.loc[cd.index, "year"] < 1914].median()), 1) if (e.loc[cd.index, "year"] < 1914).sum() else None}
    # Wikidata wreck registry around Britain (mostly national heritage records) against our counts, 1 degree cells
    wdr = json.load(open(os.path.join(ROOT, "..", "_data2", "wikidata", "wrecks.json")))
    seen = {}
    for r in wdr:
        if r["w"] in seen or r.get("regLabel") != "United Kingdom":
            continue
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r["c"])
        if m:
            seen[r["w"]] = (float(m.group(2)), float(m.group(1)))
    box = lambda la, lo: (la >= 49.5) & (la < 61) & (lo >= -8) & (lo < 2)
    wc = Counter((math.floor(la), math.floor(lo)) for la, lo in seen.values() if box(la, lo))
    ec = Counter((math.floor(la), math.floor(lo)) for la, lo in zip(e.lat, e.lon) if box(la, lo))
    cells = sorted(set(wc) | set(ec))
    rho = spearmanr([wc.get(c, 0) for c in cells], [ec.get(c, 0) for c in cells])
    R["checks"].update({"wd_registry_uk_items": len(seen), "wd_registry_cells": len(cells),
                        "wd_registry_spearman": round(float(rho.statistic), 3)})

    # overall shares
    R["overall"] = {"n": len(e), "shares": shares(e.fg, KEYS),
                    "groups": {g: int(v) for g, v in e.flag_group.value_counts().items()},
                    "british_share": round(float((e.flag_group == "British").mean()), 4),
                    "n_groups_seen": int(e.flag_group.nunique()),
                    "n_flag_texts": int(e.flag_country.nunique())}
    # eras
    R["eras"] = []
    for k, a, b, label in ERAS:
        s = e[e.era == k]
        R["eras"].append({"era": k, "label": label, "n": len(s), "per_year": round(len(s) / (b - a + 1), 1),
                          "shares": shares(s.fg, KEYS), "naval_share": round(float(s.naval.mean()), 4),
                          "effective_flags": inv_simpson(s.flag_group),
                          "top_sea": s.sea.value_counts().index[0],
                          "seas": {sea: int(v) for sea, v in s.sea.value_counts().items()}})
    # seas
    R["seas"] = []
    for sea in SEAS:
        s = e[e.sea == sea]
        own_top = s.flag_group.value_counts()
        R["seas"].append({"sea": sea, "n": len(s), "shares": shares(s.fg, KEYS),
                          "groups": {g: int(v) for g, v in own_top.items()},
                          "top": own_top.index[0], "top_share": round(float(own_top.iloc[0] / len(s)), 4),
                          "second": own_top.index[1], "second_share": round(float(own_top.iloc[1] / len(s)), 4),
                          "british_share": round(float((s.flag_group == "British").mean()), 4),
                          "effective_flags": inv_simpson(s.flag_group),
                          "top_places": [[p, int(v)] for p, v in s[s.place != ""].place.value_counts().head(5).items()],
                          "lat": round(float(s.lat.median()), 2), "lon": round(float(s.lon.median()), 2),
                          "by_era": {k: {"n": int((s.era == k).sum()), "shares": shares(s[s.era == k].fg, KEYS)} for k, *_ in ERAS}})
    R["seas_by_diversity"] = [x["sea"] for x in sorted(R["seas"], key=lambda x: -x["effective_flags"])]
    # coasts: own flag share (1816 to 1913, peacetime nineteenth century) and all years
    R["coasts"] = []
    for c, s in e.groupby("coast"):
        if len(s) < 200:
            continue
        own = OWN.get(c)
        vc = s.flag_group.value_counts()
        pre = s[(s.year >= 1816) & (s.year <= 1913)]
        R["coasts"].append({"coast": c, "n": len(s), "own_group": own,
                            "own_share": round(float((s.flag_group == own).mean()), 4) if own else None,
                            "own_share_1816_1913": round(float((pre.flag_group == own).mean()), 4) if own and len(pre) >= 50 else None,
                            "british_share": round(float((s.flag_group == "British").mean()), 4),
                            "top": vc.index[0], "top_share": round(float(vc.iloc[0] / len(s)), 4),
                            "top_foreign": [g for g in vc.index if g not in (own, "Unknown")][0],
                            "top_foreign_share": round(float(vc[[g for g in vc.index if g not in (own, "Unknown")][0]] / len(s)), 4),
                            "shares": shares(s.fg, KEYS)})
    R["coasts"].sort(key=lambda x: -x["n"])
    R["coast"] = {x["coast"]: x for x in R["coasts"]}
    other = [x for x in R["coasts"] if x["n"] >= 400 and x["coast"] not in ("United Kingdom", "Ireland")]
    R["coastcount"] = len(other)
    R["coastwins"] = sum(1 for x in other if x["top"] == "British")
    R["coast_not_british_top"] = [x["coast"] for x in other if x["top"] != "British"]
    # British share outside British and Irish coasts
    nb = e[~e.coast.isin(["United Kingdom", "Ireland"])]
    R["overall"]["british_share_off_other_coasts"] = round(float((nb.flag_group == "British").mean()), 4)
    R["overall"]["n_off_other_coasts"] = len(nb)
    R["overall"]["share_off_britain_ireland"] = round(1 - len(nb) / len(e), 4)
    # five-year series
    e["y5"] = (e.year // 5) * 5
    ser = e.groupby(["y5", "fg"]).size().unstack(fill_value=0).reindex(columns=KEYS, fill_value=0)
    ser = ser.loc[1745:]
    ser.to_csv(os.path.join(D, "flags_by_5_years.csv"))
    R["series5"] = {"start": [int(x) for x in ser.index], "keys": KEYS, "counts": {k: [int(v) for v in ser[k]] for k in KEYS}}
    bs = (ser["British"] / ser.sum(axis=1))
    bs = bs[ser.sum(axis=1) >= 200]
    R["british_share_5y"] = {"max": round(float(bs.max()), 4), "max_at": int(bs.idxmax()), "min": round(float(bs.min()), 4),
                             "min_at": int(bs.idxmin())}
    # wars
    def gshare(df, g):
        return round(float((df.flag_group == g).mean()), 4)
    ww1, pre = e[e.era == "1914 to 1918"], e[e.era == "1860 to 1913"]
    ww2 = e[e.era == "1939 to 1945"]
    R["wars"] = {"ww1_n": len(ww1), "ww2_n": len(ww2),
                 "ww1_norwegian": gshare(ww1, "Norwegian"), "pre_norwegian": gshare(pre, "Norwegian"),
                 "ww1_british": gshare(ww1, "British"), "ww1_french": gshare(ww1, "French"), "ww1_italian": gshare(ww1, "Italian"),
                 "ww2_german": gshare(ww2, "German"), "ww2_british": gshare(ww2, "British"), "ww2_italian": gshare(ww2, "Italian"),
                 "ww2_russian": gshare(ww2, "Russian"),
                 "ww2_german_naval": round(float(ww2[ww2.flag_group == "German"].naval.mean()), 4),
                 "ww2_naval": round(float(ww2.naval.mean()), 4), "ww1_naval": round(float(ww1.naval.mean()), 4),
                 "ww1_list_coords": round(float((ww1.method == "list coordinates").mean()), 4),
                 "ww2_list_coords": round(float((ww2.method == "list coordinates").mean()), 4),
                 "ww2_german_top_sea": ww2[ww2.flag_group == "German"].sea.value_counts().index[0],
                 "ww2_german_seas": {k: int(v) for k, v in ww2[ww2.flag_group == "German"].sea.value_counts().items()}}
    gn = e[(e.coast == "Norway") & (e.flag_group == "German")]
    gs = e[(e.sea == "Norwegian Sea and Arctic") & (e.flag_group == "German")]
    R["wars"]["german_off_norway_n"] = len(gn)
    R["wars"]["german_off_norway_ww2_share"] = round(float(((gn.year >= 1939) & (gn.year <= 1945)).mean()), 4)
    R["wars"]["german_norwegian_sea_ww2_share"] = round(float(((gs.year >= 1939) & (gs.year <= 1945)).mean()), 4)
    # per year counts in Europe (coverage)
    cov = pd.read_csv(os.path.join(D, "coverage_by_year.csv"))
    cov["europe_placed"] = cov.year.map(e.year.value_counts()).fillna(0).astype(int)
    cov.to_csv(os.path.join(D, "coverage_by_year.csv"), index=False)
    pk = e.year.value_counts()
    R["coverage"]["peak_year"] = int(pk.idxmax())
    R["coverage"]["peak_year_n"] = int(pk.max())
    R["coverage"]["mean_per_year_1816_1913"] = round(float(pk.reindex(range(1816, 1914), fill_value=0).mean()), 1)
    R["coverage"]["mean_per_year_1919_1938"] = round(float(pk.reindex(range(1919, 1939), fill_value=0).mean()), 1)
    R["colours"], R["colours_dark"], R["show"] = COLOURS, COLOURS_DARK, KEYS
    R["eras_def"] = [{"era": k, "label": l, "from": a, "to": b} for k, a, b, l in ERAS]
    # tables
    rows = []
    for x in R["seas"]:
        rows.append({"sea": x["sea"], "wrecks": x["n"], **{k: x["shares"][k] for k in KEYS}, "effective_flags": x["effective_flags"]})
    pd.DataFrame(rows).to_csv(os.path.join(D, "flags_by_sea.csv"), index=False)
    pd.DataFrame([{"era": x["era"], "label": x["label"], "wrecks": x["n"], **{k: x["shares"][k] for k in KEYS},
                   "naval_share": x["naval_share"]} for x in R["eras"]]).to_csv(os.path.join(D, "flags_by_era.csv"), index=False)
    pd.DataFrame([{k: v for k, v in x.items() if k != "shares"} for x in R["coasts"]]).to_csv(os.path.join(D, "flags_by_coast.csv"), index=False)
    e["flag_country"] = e["flag_country"].str.replace("\u2013", "-").str.replace("\u2014", "-")
    e["place"] = e["place"].str.replace("\u2013", "-").str.replace("\u2014", "-")
    e["ship"] = e["ship"].str.replace("\u2013", "-").str.replace("\u2014", "-")
    fm = e.groupby(["flag_country", "flag_group"]).size().reset_index(name="wrecks_in_europe").sort_values("wrecks_in_europe", ascending=False)
    fm.to_csv(os.path.join(D, "flag_mapping.csv"), index=False)
    cols = ["entry_id", "year", "month", "day", "ship", "flag_country", "flag_group", "naval", "method", "place", "lat", "lon",
            "offset_nmi", "sea", "sea_polygon", "sea_named", "coast", "page"]
    out = e[cols].copy()
    # long dashes in Wikipedia titles and names are written as hyphens in the derived files
    for c in ["ship", "flag_country", "place", "page"]:
        out[c] = out[c].str.replace("\u2013", "-").str.replace("\u2014", "-")
    out["lat"], out["lon"] = out.lat.round(4), out.lon.round(4)
    out.to_csv(os.path.join(D, "wrecks_europe.csv"), index=False)
    json.dump(R, open(os.path.join(D, "results.json"), "w"), indent=1, ensure_ascii=False)
    # page data: columnar, compact
    groups = [g for g in e.flag_group.value_counts().index]
    places = list(e.place.value_counts().index)
    pages = sorted(e.page.unique())
    pidx, gidx, sidx, pgidx = {p: i for i, p in enumerate(places)}, {g: i for i, g in enumerate(groups)}, {s: i for i, s in enumerate(SEAS)}, {p: i for i, p in enumerate(pages)}
    P = {"groups": groups, "places": places, "seas": SEAS,
         "pages": [p.replace("List of shipwrecks in ", "") for p in pages],
         "lat": [int(round(v * 100)) for v in e.lat], "lon": [int(round(v * 100)) for v in e.lon],
         "y": [int(v) for v in e.year], "g": [gidx[v] for v in e.flag_group], "n": [int(v) for v in e.naval],
         "s": [sidx[v] for v in e.sea], "p": [pidx[v] for v in e.place], "pg": [pgidx[v] for v in e.page],
         "ship": [re.sub(r"\s+", " ", v)[:40] for v in e.ship]}
    json.dump(P, open(os.path.join(D, "page.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print(json.dumps({k: R[k] for k in ["coverage", "checks", "wars", "british_share_5y"]}, indent=1))
    print("diversity", R["seas_by_diversity"])


if __name__ == "__main__":
    main()
