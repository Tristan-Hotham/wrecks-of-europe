# Whose Ships Sank Where?

Around the coasts of Europe, from the age of sail to the end of the Second World War, whose ships were lost, and where? This data study places {{coverage.europe|int}} shipwrecks from Wikipedia's lists of shipwrecks (1744 to 1945) in Europe's seas and compares the flags they sailed under, sea by sea, coast by coast and era by era.

**Interactive version:** https://tristan-hotham.github.io/wrecks-of-europe/

By Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349). Companion study: [Did Lighthouses Work?](https://tristan-hotham.github.io/did-lighthouses-work/). Blog: https://blog.tristanhotham.com/

## Headline results

- {{coverage.entries_parsed|int}} entries parsed from {{coverage.pages|int}} Wikipedia list pages; {{coverage.europe|int}} wrecks placed in a European sea.
- {{overall.british_share|pct0}} of the placed wrecks flew the British flag. In the Irish Sea and its approaches the share is {{seas.2.british_share|pct0}}; in the North Sea {{seas.0.british_share|pct0}}; in the English Channel {{seas.1.british_share|pct0}}.
- Two seas have another flag on top: the Bay of Biscay (French, {{seas.4.top_share|pct0}}) and the Norwegian Sea and Arctic (German, {{seas.7.top_share|pct0}}).
- The most mixed seas are the Kattegat and Skagerrak ({{seas.5.effective_flags|f2}} effective flags) and the Mediterranean ({{seas.8.effective_flags|f2}}); the least mixed is the Irish Sea ({{seas.2.effective_flags|f2}}).
- The British share was {{eras.1.shares.British|pct0}} in 1793 to 1815, {{wars.ww1_british|pct0}} in the First World War and {{wars.ww2_british|pct0}} in the Second.
- Norwegian ships were {{wars.ww1_norwegian|pct0}} of wrecks placed in 1914 to 1918, against {{wars.pre_norwegian|pct0}} in 1860 to 1913. German ships were the largest group in 1939 to 1945 ({{wars.ww2_german|pct0}}).
- Off the coasts of other countries (not Britain and Ireland), the British flag is the most common on {{coastwins|raw}} of {{coastcount|raw}} coasts with at least 400 wrecks.
- Hand check of 100 random placed entries: {{checks.hand.ok|int}} right, {{checks.hand.near|int}} at a county centroid, {{checks.hand.wrong|int}} wrong (two now excluded by the far-offshore rule, one fixed).

## Files

- `index.html`: the interactive page (Leaflet map of donut charts by grid square, era and flag filters, sea donuts, stacked area over time, coasts). Built by `code/build_site.py` from `code/page_template.html`; every number in the text comes from `data/results.json`. The per-wreck page data are in `data/page.json`.
- `header.png`: social card.
- `data/wrecks_europe.csv`: one row per wreck placed in a European sea: date, ship, flag as written, flag group, naval ensign, how it was placed (`method`), the place named, latitude and longitude, offset in nautical miles where given, sea area, Natural Earth marine polygon, sea named in the description, nearest coast, and the Wikipedia list page. The descriptions themselves are on Wikipedia.
- `data/flags_by_sea.csv`, `data/flags_by_era.csv`, `data/flags_by_coast.csv`, `data/flags_by_5_years.csv`: the summary tables.
- `data/flag_mapping.csv`: every flag name met in European wrecks and the group it was put in.
- `data/coverage_by_year.csv`: entries parsed per year and wrecks placed in Europe per year.
- `data/hand_check.csv`: the 100-entry hand check of the location rule with verdicts and notes.
- `data/sea_areas_ne10m.geojson`, `data/europe_countries_ne50m.geojson`: the Natural Earth layers used (clipped and simplified).
- `data/results.json`: every number used on the page, in the paper, the blog and the collage.
- `code/`: Python scripts, run in order by `code/run_all.sh`. `flags.py` holds the flag merges and `02_locate.py` the location rule; these are the places to audit the study.

## How to rerun

Inputs (not included): the wikitext of the "List of shipwrecks" pages (a JSON of page title to wikitext), the coordinates of the pages they link to (a JSON from the Wikipedia API: `{"coords": {title: [lat, lon]}, "redirects": {...}}`), a Wikidata SPARQL export of shipwrecks with coordinates, and the Natural Earth 1:50m admin 0 countries and 1:10m marine polygons.

```
sh code/run_all.sh
```

Python 3 with pandas, numpy, scipy, shapely and pyproj; matplotlib for the figures.

## Method in brief

Each entry's description is cut down to the part about the loss (the voyage, later events and other ships in brackets are removed). The position is the coordinates given in the list if any; else the Wikidata wreck position of the ship's own article if it agrees with the text; else the first linked place with coordinates that is not a whole sea, country or large region. Wrecks are kept if they fall in Europe's seas (30 to 72 N, 25 W to 42 E, without the Atlantic south of 36 N, the Suez Canal, lakes, or places more than 50 km inland); losses more than 60 nautical miles from the named place are left out. Seas are the nearest Natural Earth marine area, grouped into ten. Flags are grouped across eras (for example Prussia and the Hanseatic cities into German).

Caveats: the lists are a British record, compiled largely from Lloyd's List and British newspapers, so the British share is a share of the record, not of all losses; coverage changes between eras; the position is the place named, not the exact spot.

## Sources and licence

- Wreck records: Wikipedia contributors, "List of shipwrecks" pages, CC BY-SA 4.0. Largely compiled by Wikipedia editors from Lloyd's List and contemporary newspapers.
- Coordinates of linked places: Wikipedia, via the MediaWiki API (CC BY-SA 4.0).
- Wreck positions: Wikidata, CC0.
- Sea areas and land: Natural Earth (public domain), https://www.naturalearthdata.com/
- Base map on the page: tiles © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

Because the wreck data derive from Wikipedia, the derived data and the text of the page are released under CC BY-SA 4.0. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. (2026) *Whose Ships Sank Where? Flags of shipwrecks in Europe's seas, 1744 to 1945*. Zenodo. https://doi.org/10.5281/zenodo.23677833

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
