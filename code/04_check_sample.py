"""Step 4: the hand check of the location rule.

A random sample of 100 located European entries (pandas sample, random_state=2026, drawn from
the first full run of 03_areas.py) was read one by one, comparing the description with the
place chosen. Verdicts are stored in data/hand_check.csv:
  ok    the chosen place is where the description says the ship was lost (within about 20 km)
  near  the chosen place is a county or region centroid containing the place (20 to 50 km)
  wrong the chosen place is not where the ship was lost
This script summarises the verdicts and reports what the final rules now do with each entry.
Usage: python3 code/04_check_sample.py  (to draw a fresh sample: --draw)
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
e = pd.read_csv(os.path.join(ROOT, "work", "europe.csv.gz"), keep_default_na=False, low_memory=False)
if "--draw" in sys.argv:
    s = e.sample(100, random_state=2026)[["entry_id", "year", "ship", "flag_group", "method", "place", "lat", "lon", "desc"]]
    s.to_csv(os.path.join(ROOT, "work", "check_sample.csv"), index=False)
    for _, r in s.iterrows():
        print(f"{r.entry_id}|{r.method[:5]}|{r.place}|{r.lat:.2f},{r.lon:.2f}|{r.desc[:230]}")
    sys.exit()
h = pd.read_csv(os.path.join(ROOT, "data", "hand_check.csv"), keep_default_na=False)
still = h.entry_id.isin(e.entry_id)
out = {"n": len(h), "ok": int((h.verdict == "ok").sum()), "near": int((h.verdict == "near").sum()),
       "wrong": int((h.verdict == "wrong").sum()),
       "wrong_now_dropped": int(((h.verdict == "wrong") & ~still).sum()),
       "kept_now": int(still.sum())}
k = h[still]
out["accuracy_kept_ok_or_near"] = round(float((k.verdict != "wrong").mean()), 3)
out["accuracy_kept_ok"] = round(float((k.verdict == "ok").mean()), 3)
json.dump(out, open(os.path.join(ROOT, "work", "hand_check_summary.json"), "w"), indent=1)
print(out)
