"""Step 7: ../header.png, the 1200 x 630 social card (matplotlib)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mapdraw import ROOT, R, fonts, draw_land, extent, load_wrecks, cells, donut

DISP, SER, MONO = fonts()
BG, FG, MUT, TEAL, LAND, SEA = "#F4EFE3", "#14284B", "#5E6676", "#0E6E73", "#E2D8C0", "#DCE6E4"
e = load_wrecks()
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([0.5, 0.0, 0.5, 1.0], facecolor=SEA)
draw_land(ax, fc=LAND)
extent(ax, -12, 35, 32, 64)
ax.set_aspect("equal", adjustable="datalim")
ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
c = cells(e, km=260, min_n=40)
mx = c.n.max()
for _, r in c.iterrows():
    rad = 45 + 230 * np.sqrt(r.n / mx)
    donut(ax, r.x, r.y, rad, {k: r.get(k, 0) for k in R["show"]}, width=0.5, edge=SEA, lw=0.5)
fig.text(0.055, 0.86, "DATA STUDY", fontsize=13, family=MONO, color="white", va="center",
         bbox=dict(boxstyle="square,pad=0.45", fc=TEAL, ec="none"))
fig.text(0.175, 0.86, "EUROPE'S SEAS, 1744 TO 1945", fontsize=13, family=MONO, color=MUT, va="center")
fig.text(0.052, 0.77, "Whose ships\nsank where?", fontproperties=DISP, fontsize=56, color=FG, va="top", linespacing=0.92)
fig.text(0.055, 0.40, f"{R['coverage']['europe']:,} wrecks from Wikipedia's\nshipwreck lists, by the flag\nthey sailed under.",
         family=SER, fontsize=21, color=FG, va="top", linespacing=1.2)
fig.text(0.055, 0.085, "Dr Tristan Hotham · Independent researcher", family=MONO, fontsize=12.5, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG)
print("header.png")
