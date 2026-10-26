"""Step 2: give every entry a flag group and, where possible, a place of loss.

This step collects the candidate positions; 03_areas.py chooses between them.
Location rule (applied in this order; the first that succeeds wins):
  1. A {{coord}} template in the loss text (exact position given by the list).
  2. Wikidata: the ship has an English Wikipedia article (from the ship cell) that Wikidata
     links to a wreck item with coordinates (CC0). Used only if it agrees with the text
     (within 150 km of the place in rule 3) or if the text gives no place at all.
  3. The first linked place in the loss text that has coordinates and is not a "broad"
     area (an ocean, a named sea, a country or a large region).
  If none succeeds but the loss text links a named sea, the entry gets that sea but no point.

The "loss text" is the description with the parts that are not about the loss removed:
  * everything from a voyage phrase onwards in a sentence ("on a voyage from X to Y",
    "bound for", "en route", "from X for Y"),
  * whole sentences about what happened later or elsewhere (refloated, taken in to, towed,
    put into, arrived, landed, rescued by, departed, sailed from, wreckage, survivors, condemned),
  * text in brackets (flags and names of other ships, attackers),
  * links to ship articles.
Offsets such as "13 nmi north east of Ushant" are not applied: the point is the named place.
The offset in nautical miles, when given, is kept in `offset_nmi`.

Inputs : work/entries.csv.gz, _data2/wikipedia_link_coords.json, _data2/wikidata/wrecks.json
Output : work/located.csv.gz (all entries with flag group and location fields)
"""
import gzip
import json
import math
import os
import re
import sys
import urllib.parse

import pandas as pd

from flags import flag_country, flag_group
from wikitext import _template_text, SHIP_PREFIX

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SHARED = os.path.join(ROOT, "..", "_data2")

LC = json.load(open(os.path.join(SHARED, "wikipedia_link_coords.json")))
COORDS, REDIR = LC["coords"], LC["redirects"]

# ---- the vocabulary of named seas used for sea areas -------------------------------------
SEA_OF = {
    "North Sea": "North Sea", "Dogger Bank": "North Sea", "German Bight": "North Sea", "Heligoland Bight": "North Sea",
    "Wadden Sea": "North Sea", "Southern Bight": "North Sea",
    "English Channel": "English Channel", "Strait of Dover": "English Channel", "Dover Strait": "English Channel",
    "The Downs": "English Channel", "Solent": "English Channel",
    "Irish Sea": "Irish Sea and approaches", "St George's Channel": "Irish Sea and approaches",
    "Bristol Channel": "Irish Sea and approaches", "North Channel (Great Britain and Ireland)": "Irish Sea and approaches",
    "Celtic Sea": "Irish Sea and approaches", "Western Approaches": "Irish Sea and approaches",
    "Atlantic Ocean": "Atlantic", "North Atlantic Ocean": "Atlantic", "North Atlantic": "Atlantic",
    "Bay of Biscay": "Bay of Biscay",
    "Baltic Sea": "Baltic", "Gulf of Finland": "Baltic", "Gulf of Bothnia": "Baltic", "Gulf of Riga": "Baltic",
    "Bothnian Sea": "Baltic", "Bothnian Bay": "Baltic", "Gulf of Danzig": "Baltic", "Bay of Gdańsk": "Baltic",
    "Øresund": "Baltic", "Oresund": "Baltic", "The Sound": "Baltic", "Great Belt": "Baltic", "Little Belt": "Baltic",
    "Kattegat": "Kattegat and Skagerrak", "Skagerrak": "Kattegat and Skagerrak",
    "Norwegian Sea": "Norwegian Sea and Arctic", "Barents Sea": "Norwegian Sea and Arctic", "White Sea": "Norwegian Sea and Arctic",
    "Arctic Ocean": "Norwegian Sea and Arctic", "Greenland Sea": "Norwegian Sea and Arctic", "Kara Sea": "Norwegian Sea and Arctic",
    "Mediterranean Sea": "Mediterranean", "Adriatic Sea": "Mediterranean", "Aegean Sea": "Mediterranean",
    "Ionian Sea": "Mediterranean", "Tyrrhenian Sea": "Mediterranean", "Ligurian Sea": "Mediterranean",
    "Alboran Sea": "Mediterranean", "Balearic Sea": "Mediterranean", "Gulf of Lion": "Mediterranean",
    "Sea of Crete": "Mediterranean", "Levantine Sea": "Mediterranean", "Strait of Gibraltar": "Mediterranean",
    "Gulf of Genoa": "Mediterranean", "Strait of Messina": "Mediterranean", "Strait of Sicily": "Mediterranean",
    "Libyan Sea": "Mediterranean", "Myrtoan Sea": "Mediterranean", "Gulf of Corinth": "Mediterranean", "Dardanelles": "Mediterranean",
    "Black Sea": "Black Sea", "Sea of Azov": "Black Sea", "Sea of Marmara": "Black Sea", "Bosphorus": "Black Sea",
    "Kerch Strait": "Black Sea",
}
SEAS = ["North Sea", "English Channel", "Irish Sea and approaches", "Atlantic", "Bay of Biscay", "Kattegat and Skagerrak",
        "Baltic", "Norwegian Sea and Arctic", "Mediterranean", "Black Sea"]
# straits and small seas above are specific enough to locate a wreck; these are not
BROAD_SEA = {"North Sea", "English Channel", "Irish Sea", "Celtic Sea", "Western Approaches", "Atlantic Ocean",
             "North Atlantic Ocean", "North Atlantic", "Bay of Biscay", "Baltic Sea", "Gulf of Finland", "Gulf of Bothnia",
             "Bothnian Sea", "Bothnian Bay", "Gulf of Riga", "Kattegat", "Skagerrak", "Norwegian Sea", "Barents Sea", "White Sea",
             "Arctic Ocean", "Greenland Sea", "Kara Sea", "Mediterranean Sea", "Adriatic Sea", "Aegean Sea", "Ionian Sea",
             "Tyrrhenian Sea", "Ligurian Sea", "Alboran Sea", "Balearic Sea", "Levantine Sea", "Libyan Sea", "Sea of Crete",
             "Black Sea", "Sea of Azov", "Sea of Marmara", "St George's Channel", "Bristol Channel", "Dogger Bank", "German Bight",
             "Heligoland Bight", "Wadden Sea", "Pacific Ocean", "Indian Ocean", "Southern Ocean", "Caribbean Sea", "Gulf of Mexico",
             "South Atlantic Ocean", "South China Sea", "Red Sea", "Gulf of Lion", "Myrtoan Sea", "Southern Bight", "Gulf of Genoa"}
BROAD_RE = re.compile(r"(Ocean|\bSea)$|^(Sea|Gulf) of |^Bay of Biscay$", re.I)
# countries, former states and very large regions (centroids are far from any coast)
BROAD_LAND = set("""Europe|Africa|Asia|America|North America|South America|Scandinavia|Iberian Peninsula|Balkans|British Isles|
Great Britain|United Kingdom|United Kingdom of Great Britain and Ireland|Kingdom of Great Britain|England|Scotland|Wales|Ireland|
Ireland (island)|Kingdom of Ireland|Northern Ireland|Irish Free State|France|Kingdom of France|Spain|Portugal|Netherlands|Dutch Republic|
Batavian Republic|United Kingdom of the Netherlands|Belgium|Germany|German Empire|Nazi Germany|Weimar Republic|Prussia|Kingdom of Prussia|
Denmark|Denmark–Norway|Norway|Sweden|Finland|Grand Duchy of Finland|Russia|Russian Empire|Soviet Union|Poland|Estonia|Latvia|
Lithuania|Italy|Kingdom of Italy|Greece|Kingdom of Greece|Turkey|Ottoman Empire|Austria-Hungary|Austrian Empire|Yugoslavia|
Kingdom of Yugoslavia|Albania|Romania|Kingdom of Romania|Bulgaria|Kingdom of Bulgaria|Ukraine|Crimea|Morocco|Algeria|Tunisia|
Libya|Egypt|Kingdom of Egypt|Syria|Lebanon|Palestine|Mandatory Palestine|Iceland|Faroe Islands|Holland|Jutland|Norrland|Lapland|
Sardinia|Sicily|Corsica|Crete|Cyprus|Malta|Brittany|Normandy|Flanders|Galicia (Spain)|Andalusia|Catalonia|Provence|Gascony|
Kingdom of Sardinia|Kingdom of the Two Sicilies|Papal States|Hanover|Kingdom of Hanover|Schleswig-Holstein|Schleswig|Holstein|
Mecklenburg|Pomerania|Swedish Pomerania|East Prussia|West Prussia|Courland|Livonia|Estonia (Russian Empire)|Highlands|
Scottish Highlands|Hebrides|Outer Hebrides|Inner Hebrides|Orkney|Shetland|Frisian Islands|West Frisian Islands|East Frisian Islands|
North Frisian Islands|Channel Islands|Socialist Federal Republic of Yugoslavia|Ottoman Syria|Spanish protectorate in Morocco|
Grand Duchy of Tuscany|Kingdom of Sicily|Courland Governorate|Duchy of Schleswig|Province of Pomerania (1815–1945)|Kingdom of Naples|
Peloponnese|Morea|Calabria|Apulia|Lazio|Veneto|Istria|Asturias|Algarve|Zealand|United States|Canada|Australia|India|British India|British Raj|Netherlands East Indies|
West Indies|British America|British North America|New South Wales|Newfoundland (island)|Newfoundland Colony|Dominion of Newfoundland"""
                 .replace("\n", "").split("|"))

SHIP_TITLE = re.compile(r"^(%s)\s|^(German|French|Italian|British|Soviet|Russian|Japanese|Dutch|Norwegian|Swedish|Danish|Greek|"
                        r"Spanish|Portuguese|Turkish|Ottoman|Austro-Hungarian|Polish|Yugoslav|Romanian|Finnish|Estonian|Latvian|"
                        r"Belgian|American|Royal Navy|Confederate)\s+(submarine|ship|cruiser|destroyer|battleship|frigate|"
                        r"torpedo boat|minesweeper|gunboat|corvette|sloop|aircraft|minelayer|auxiliary|tanker|patrol|motor|"
                        r"landing|seaplane|trawler|steamer|schooner|brig|barque|ironclad|ship-of-the-line|monitor|aviso|escort|"
                        r"armoured|armored|coastal|training|survey|hospital|transport)|^(U|UB|UC|UA|S)-\d|\(ship\)|\(\d{4}\)$"
                        % "|".join(SHIP_PREFIX))

CUT_RE = re.compile(r"\b(whilst|while|when)?\s*(on (a|her|the|his) (voyage|passage|maiden voyage|return voyage)|bound (for|from|to)|"
                    r"en route|sailing from|sailing to|in tow|under tow|being towed|towing)\b|\bfrom\s+\x00\d+\x01[^.;]{0,60}?\s(to|for)\s+\x00",
                    re.I)
DROP_RE = re.compile(r"\b(refloated|taken in(to)?|towed|put in(to)?|put back|arrived|landed|rescued by|brought in(to)?|departed|"
                     r"sailed from|wreckage|survivors|condemned|later|subsequently|salvaged|raised|was sold|broken up|scuttled by her crew|"
                     r"no further trace|presumed|collided with|in collision with)\b", re.I)
LOSS_RE = re.compile(r"\b(wreck|wrecked|sank|sunk|sink|founder|foundered|ashore|aground|struck|lost|destroyed|burnt|burned|"
                     r"abandoned|capsized|beached|stranded|exploded|blew up|scuttled|captured|seized|torpedoed|mined|bombed|"
                     r"went down|run down|ran down|collided|collision|grounded|broke|caught fire|fire|disappeared|missing|damaged|"
                     r"holed|swamped|upset|bilged|leak|scuttled|shelled|rammed|attacked|overwhelmed|overturned|driven|went to pieces|"
                     r"put on shore|run on shore|on shore|off|near|at|in)\b", re.I)
DIST_RE = re.compile(r"(\d[\d,.]*)\s*(nmi|nautical miles?|miles?|mi|km|kilometres?|leagues?)\b", re.I)


def norm_title(t):
    t = urllib.parse.unquote(t.split("#")[0]).replace("_", " ").strip()
    return (t[:1].upper() + t[1:]) if t else t


# links whose target is wrong in the lists themselves, found while checking the most common places:
# [[Lubawka|Liebau]] (an inland town in Silesia) is used for Liebau in Courland, now Liepaja.
# [[Llanelly]] goes to a village in Monmouthshire; in these lists it always means the port of Llanelli
# (found in the hand check, 04_check_sample.py).
LABEL_FIX = {("Lubawka", "Liebau"): "Liepāja", ("Lubawka", "Libau"): "Liepāja", ("Llanelly", ""): "Llanelli"}


def resolve(t, label=""):
    t = norm_title(t)
    for (tt, lab), new in LABEL_FIX.items():
        if t == tt and label.strip().startswith(lab):
            t = new
    for _ in range(3):
        if t in COORDS:
            return t, COORDS[t]
        if t in REDIR:
            t = REDIR[t]
        else:
            break
    return t, COORDS.get(t)


def parse_coord(body):
    """{{coord|48|41|N|5|08|W}}, {{coord|50.1|-4.2}}, {{coord|48|41|30|N|5|8|10|W}} -> (lat, lon)."""
    parts = [p.strip() for p in body.split("|")[1:] if "=" not in p and p.strip()]
    try:
        if "N" in parts or "S" in parts:
            i = parts.index("N") if "N" in parts else parts.index("S")
            lat = sum(float(x) / 60 ** k for k, x in enumerate(parts[:i]))
            lat = -lat if parts[i] == "S" else lat
            rest = parts[i + 1:]
            j = rest.index("E") if "E" in rest else rest.index("W")
            lon = sum(float(x) / 60 ** k for k, x in enumerate(rest[:j]))
            lon = -lon if rest[j] == "W" else lon
        else:
            lat, lon = float(parts[0]), float(parts[1])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (ValueError, IndexError):
        pass
    return None


def tokenise(w):
    """Replace links and coord templates by placeholders \x00k\x01; render other templates as text."""
    toks = []

    def link(m):
        target = m.group(1)
        label = m.group(2) if m.group(2) is not None else target
        if re.match(r"(File|Image|Category):", target, re.I):
            return ""
        toks.append(("link", target, label))
        return f"\x00{len(toks) - 1}\x01"

    s = w
    for _ in range(12):
        new = re.sub(r"\{\{\s*coord\s*(\|[^{}]*)\}\}", lambda m: (toks.append(("coord", m.group(1), "")), f"\x00{len(toks) - 1}\x01")[1], s, flags=re.I)
        new = re.sub(r"\{\{([^{}]*)\}\}", lambda m: _template_text(m.group(1)), new)
        if new == s:
            break
        s = new
    s = re.sub(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]", link, s)
    s = s.replace("'''", "").replace("''", "")
    return s, toks


def loss_text(w):
    s, toks = tokenise(w)
    s = re.sub(r"^\s*(World War I{1,2}|\x00\d+\x01)\s*:\s*", "", s)   # "World War I:" prefix
    # keep coordinates even inside brackets, drop all other bracketed text
    s = re.sub(r"\(([^()]*)\)", lambda m: " " + " ".join(re.findall(r"\x00\d+\x01", m.group(1))
                                                         if any(toks[int(k)][0] == "coord" for k in re.findall(r"\x00(\d+)\x01", m.group(1))) else []) + " ", s)
    sents = re.split(r"(?<=[.;])\s+(?=[A-Z\x00])", s)
    keep = []
    for k, sent in enumerate(sents):
        if k > 0 and DROP_RE.search(sent):
            continue
        if k == 0 and DROP_RE.search(sent) and re.match(r"\s*(The|She|He|It)\b[^.]{0,40}\b(departed|sailed from)", sent):
            continue
        m = CUT_RE.search(sent)
        if m:
            sent = sent[:m.start()]
        keep.append(sent)
    return " ".join(keep), toks


def locate(w):
    """Return dict with method, place, lat, lon, sea_named, offset_nmi."""
    text, toks = loss_text(w)
    ids = [int(k) for k in re.findall(r"\x00(\d+)\x01", text)]
    out = {"place": "", "link_lat": None, "link_lon": None, "coord_lat": None, "coord_lon": None, "sea_named": "", "offset_nmi": None}
    for i in ids:
        kind, target, label = toks[i]
        if kind == "link":
            t = norm_title(target)
            t2 = REDIR.get(t, t)
            sea = SEA_OF.get(t) or SEA_OF.get(t2)
            if sea and not out["sea_named"]:
                out["sea_named"] = sea
    # sea names written without a link ("in the North Sea") also count
    if not out["sea_named"]:
        plain_txt = re.sub(r"\x00(\d+)\x01", lambda m: toks[int(m.group(1))][2], text)
        for name, sea in SEA_OF.items():
            if len(name) > 6 and re.search(r"\b" + re.escape(name) + r"\b", plain_txt):
                out["sea_named"] = sea
                break
    for i in ids:
        if toks[i][0] == "coord":
            c = parse_coord(toks[i][1])
            if c:
                out["coord_lat"], out["coord_lon"] = c
                break
    # links before the first loss word describe the ship ("The Dartmouth ship was ..."), not the place
    lv = LOSS_RE.search(text)
    start = lv.start() if lv else 0
    for i in ids:
        kind, target, label = toks[i]
        if kind != "link" or text.find(f"\x00{i}\x01") < start:
            continue
        t, c = resolve(target, label)
        if c is None or SHIP_TITLE.search(t) or SHIP_TITLE.search(norm_title(target)):
            continue
        if t in BROAD_SEA or t in BROAD_LAND or norm_title(target) in BROAD_LAND or BROAD_RE.search(t):
            continue
        out.update(place=t, link_lat=c[0], link_lon=c[1])
        # distance before the place ("40 nmi off X")
        pre = re.sub(r"\x00\d+\x01", " ", text[:text.find(f"\x00{i}\x01")])[-60:]
        d = list(DIST_RE.finditer(pre))
        if d:
            try:
                v = float(d[-1].group(1).replace(",", ""))
                u = d[-1].group(2).lower()
                out["offset_nmi"] = round(v * (0.54 if u.startswith("k") else 0.87 if u in ("mi", "mile", "miles") else 3 if u.startswith("league") else 1), 1)
            except ValueError:
                pass
        break
    return out, text, toks


def ship_article(sw):
    """Title of the ship's own article, if the ship cell links one."""
    sw = sw or ""
    m = re.search(r"\{\{\s*([A-Za-zÉ]+)\s*\|([^{}|]*)\|?([^{}|]*)", sw)
    if m and (m.group(1) in SHIP_PREFIX or m.group(1).upper() in SHIP_PREFIX or m.group(1) in ("SMU", "GS")):
        pre = {"SMU": "SM", "GS": "German submarine"}.get(m.group(1), m.group(1))
        name, yr = m.group(2).strip(), m.group(3).strip()
        if m.group(1) == "GS":
            return f"German submarine {name}" + (f" ({yr})" if yr else "")
        return f"{pre} {name}" + (f" ({yr})" if yr else "")
    m = re.search(r"\{\{\s*ship\s*\|([^{}|]*)\|([^{}|]*)\|?([^{}|]*)", sw, re.I)
    if m:
        return " ".join(x for x in [m.group(1).strip(), m.group(2).strip()] if x) + (f" ({m.group(3).strip()})" if m.group(3).strip() and m.group(3).strip()[:1].isdigit() else "")
    m = re.search(r"\[\[([^\]|]*)", sw)
    return norm_title(m.group(1)) if m else ""


def wikidata_index():
    w = json.load(open(os.path.join(SHARED, "wikidata", "wrecks.json")))
    idx = {}
    for r in w:
        if not r.get("enwiki"):
            continue
        m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r.get("c", ""))
        if not m:
            continue
        t = norm_title(r["enwiki"].rsplit("/wiki/", 1)[1])
        idx.setdefault(t, (float(m.group(2)), float(m.group(1)), r["w"]))
    return idx


def km(a, b, c, d):
    p = math.pi / 180
    h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def main():
    e = pd.read_csv(os.path.join(ROOT, "work", "entries.csv.gz"), dtype=str, keep_default_na=False)
    fc = e["flag_raw"].map(flag_country)
    e["flag_country"] = fc.str[0]
    e["naval"] = fc.str[1].astype(int)
    e["flag_group"] = e["flag_country"].map(flag_group)
    wd = wikidata_index()
    rows = []
    for w, sw in zip(e["desc_wiki"], e["ship_wiki"]):
        o, _, _ = locate(w)
        art = ship_article(sw)
        o["ship_article"] = art
        o["wd_item"], o["wd_lat"], o["wd_lon"] = "", None, None
        hit = (wd.get(art) or wd.get(REDIR.get(art, ""))) if art else None
        if hit:
            o["wd_lat"], o["wd_lon"], o["wd_item"] = hit
        rows.append(o)
    loc = pd.DataFrame(rows)
    out = pd.concat([e.drop(columns=["desc_wiki", "ship_wiki", "flag_raw"]), loc], axis=1)
    out.to_csv(os.path.join(ROOT, "work", "located.csv.gz"), index=False, compression="gzip")
    print("link", out["link_lat"].notna().sum(), "coord", out["coord_lat"].notna().sum(), "wikidata", out["wd_lat"].notna().sum())
    print("sea named:", (out["sea_named"] != "").sum())


if __name__ == "__main__":
    main()
