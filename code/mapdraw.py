"""Shared helpers for the static maps (header, paper, blog, collage): projection, land, donuts.

Projection: ETRS89 Lambert azimuthal equal-area (EPSG:3035), in km.
Land: data/europe_countries_ne50m.geojson (Natural Earth, public domain), written by 03_areas.py.
"""
import json
import math
import os

import numpy as np
import pandas as pd
from matplotlib.patches import Wedge, Polygon, Circle
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
FONTS = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
KEYS = R["show"]
COL = R["colours"]


def fonts():
    from matplotlib import font_manager as fm
    for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf",
              "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
        p = os.path.join(FONTS, f)
        if os.path.exists(p):
            fm.fontManager.addfont(p)
    p = os.path.join(FONTS, "FrauncesVar.ttf")
    disp = fm.FontProperties(fname=p, weight=900) if os.path.exists(p) else fm.FontProperties(family="serif", weight="bold")
    return disp, "Source Serif 4", "IBM Plex Mono"


def xy(lon, lat):
    x, y = T.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.asarray(x) / 1000, np.asarray(y) / 1000


def draw_land(ax, fc="#E5DCC6", ec="none", lw=0.4, z=1):
    g = json.load(open(os.path.join(ROOT, "data", "europe_countries_ne50m.geojson")))
    for f in g["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]] if geom["type"] == "Polygon" else []
        for poly in polys:
            ring = np.array(poly[0])
            if len(ring) < 3:
                continue
            X, Y = xy(ring[:, 0], ring[:, 1])
            ax.add_patch(Polygon(np.c_[X, Y], closed=True, fc=fc, ec=ec, lw=lw, zorder=z))


def extent(ax, lon0=-12, lat0=34, lon1=40, lat1=70):
    """Set limits from a lon/lat box (corners projected)."""
    lo = np.linspace(lon0, lon1, 30); la = np.linspace(lat0, lat1, 30)
    X1, Y1 = xy(np.r_[lo, lo, np.full(30, lon0), np.full(30, lon1)], np.r_[np.full(30, lat0), np.full(30, lat1), la, la])
    ax.set_xlim(X1.min(), X1.max()); ax.set_ylim(Y1.min(), Y1.max()); ax.set_aspect("equal"); ax.axis("off")


def load_wrecks():
    e = pd.read_csv(os.path.join(ROOT, "data", "wrecks_europe.csv"), keep_default_na=False, low_memory=False)
    e["fg"] = e.flag_group.where(e.flag_group.isin(KEYS), "Other")
    e["x"], e["y"] = xy(e.lon.values, e.lat.values)
    return e


def cells(e, km=200, min_n=1):
    """Aggregate wrecks into square cells of `km` in the projection; donut at the members' mean position."""
    k = np.floor(e.x / km).astype(int).astype(str) + ":" + np.floor(e.y / km).astype(int).astype(str)
    g = e.assign(k=k).groupby("k")
    out = g.agg(n=("x", "size"), x=("x", "mean"), y=("y", "mean")).reset_index()
    by = e.assign(k=k).groupby(["k", "fg"]).size().unstack(fill_value=0)
    out = out.merge(by, left_on="k", right_index=True)
    return out[out.n >= min_n].sort_values("n", ascending=False)


def donut(ax, x, y, r, counts, width=0.45, z=5, edge="#F4EFE3", lw=0.6, colours=None):
    colours = colours or COL
    tot = sum(counts.values())
    a = 90.0
    for k in KEYS:
        v = counts.get(k, 0)
        if not v:
            continue
        da = v / tot * 360
        ax.add_patch(Wedge((x, y), r, a - da, a, width=r * width, fc=colours[k], ec=edge, lw=lw, zorder=z))
        a -= da


def legend_items():
    return [(k if k not in ("Other", "Unknown") else {"Other": "Other flags", "Unknown": "Flag unknown"}[k], COL[k]) for k in KEYS]
