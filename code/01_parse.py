"""Step 1: parse every "List of shipwrecks in ..." page into one row per entry.

Extends parse_wrecks.py from the companion project "Did Lighthouses Work?"
(https://github.com/Tristan-Hotham/did-lighthouses-work): same date and text rules,
plus three things this study needs:
  * the raw flag cell, so flags can be normalised across eras (02_flags.py),
  * whether the flag template is a naval one ({{navy}}, {{naval}}),
  * the description's wikitext (references removed), so the links in it can be located (03_locate.py).

Input : hist_wrecks_wikitext.json  {page title: wikitext}
Output: work/entries.csv.gz   one row per entry, 1700 to 1945
        data/coverage_by_year.csv

Usage: python3 code/01_parse.py <hist_wrecks_wikitext.json>
"""
import csv
import gzip
import json
import os
import re
import sys
from collections import Counter

from wikitext import plain, split_params, extract_templates

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MON_RE = "|".join(MONTHS)


def parse_date(s):
    s = plain(s)
    m = re.search(r"(\d{1,2})\s+(%s)" % MON_RE, s)
    if m:
        return MONTHS.index(m.group(2)) + 1, int(m.group(1))
    m = re.search(r"(%s)\s+(\d{1,2})\b(?!\d)" % MON_RE, s)
    if m:
        return MONTHS.index(m.group(1)) + 1, int(m.group(2))
    m = re.search(r"(%s)" % MON_RE, s)
    if m:
        return MONTHS.index(m.group(1)) + 1, None
    return None, None


def clean_wiki(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/\s*>", "", s, flags=re.S | re.I)
    s = re.sub(r"<ref[^>]*>.*?</ref\s*>", "", s, flags=re.S | re.I)
    s = re.sub(r"\{\{\s*(?:sfn|efn|citation needed|cn|clarify|which|when|dubious)[^{}]*\}\}", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def parse_page(title, text):
    tm = re.search(r"List of shipwrecks in (?:(%s) )?(\d{4})" % MON_RE, title)
    if not tm:
        return []
    page_month = MONTHS.index(tm.group(1)) + 1 if tm.group(1) else None
    year = int(tm.group(2))
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    marks = []
    for m in re.finditer(r"^(={2,4})\s*(.*?)\s*\1\s*$", text, flags=re.M):
        marks.append((m.start(), "h", m.group(2)))
    for i, j, body in extract_templates(text, r"\{\{\s*shipwreck list begin"):
        d = re.search(r"\|\s*date\s*=([^|]*)", body)
        if d:
            marks.append((i, "b", d.group(1)))
    marks.sort()
    rows = []
    for i, j, body in extract_templates(text, r"\{\{\s*shipwreck list item"):
        params = {}
        for p in split_params(body)[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k.strip().lower()] = v
        month, day = page_month, None
        for pos, kind, val in reversed([mk for mk in marks if mk[0] < i]):
            mo, dy = parse_date(val)
            if mo is None and re.search(r"unknown", val, re.I):
                break
            if mo is not None:
                month, day = mo, dy
                break
        ship_raw = params.get("ship", "").strip()
        ship = plain(ship_raw)
        desc_w = clean_wiki(params.get("desc", ""))
        desc = plain(desc_w)
        if not (ship or desc):
            continue
        rows.append({"page": title, "year": year, "month": month or "", "day": day or "",
                     "ship": ship, "ship_wiki": clean_wiki(ship_raw),
                     "flag_raw": clean_wiki(params.get("flag", "")), "desc": desc, "desc_wiki": desc_w})
    return rows


def main(src):
    pages = json.load(open(src, encoding="utf-8"))
    out, redirects = [], 0
    for title in sorted(pages):
        text = pages[title]
        if text.lstrip().upper().startswith("#REDIRECT"):
            redirects += 1
            continue
        out.extend(parse_page(title, text))
    out.sort(key=lambda r: (r["year"], r["month"] or 13, r["day"] or 32))
    for k, r in enumerate(out):
        r["entry_id"] = k + 1
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    cols = ["entry_id", "year", "month", "day", "ship", "ship_wiki", "flag_raw", "desc", "desc_wiki", "page"]
    with gzip.open(os.path.join(ROOT, "work", "entries.csv.gz"), "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    by_year = Counter(r["year"] for r in out)
    with open(os.path.join(ROOT, "data", "coverage_by_year.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "entries_parsed"])
        for y in range(1700, 1946):
            w.writerow([y, by_year.get(y, 0)])
    print(f"pages {len(pages)}, redirects skipped {redirects}, entries {len(out)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/Downloads/hist_wrecks_wikitext.json")
