"""Step 6: build ../index.html from page_template.html.

Every number in the text is a placeholder like {{seas.0.british_share|pct0}} filled from
../data/results.json. The results needed by the charts are embedded as `const R = ...`;
the per-wreck page data are loaded from data/page.json.
Formats: int (thousands commas), pct0, pct1, f1, f2, raw.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    return str(v)


def fill(text):
    return re.sub(r"\{\{([^{}|]+?)(?:\|(\w+))?\}\}", lambda m: fmt(get(m.group(1).strip()), m.group(2) or "raw"), text)


if __name__ == "__main__":
    t = fill(open(os.path.join(HERE, "page_template.html")).read())
    keep = {k: R[k] for k in ["show", "overall", "eras_def", "eras", "seas", "series5", "coasts"]}
    for s in keep["seas"]:
        s.pop("by_era", None)
    t = t.replace("/*DATA*/", "const R = " + json.dumps(keep, separators=(",", ":"), ensure_ascii=False) + ";")
    open(os.path.join(ROOT, "index.html"), "w").write(t)
    print("index.html", len(t.encode()) // 1024, "KB")
    open(os.path.join(ROOT, "README.md"), "w").write(fill(open(os.path.join(HERE, "README_template.md")).read()))
    print("README.md")
