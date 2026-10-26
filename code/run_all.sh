#!/bin/sh
# Rebuild everything from the raw inputs. Usage (from the repository root):
#   sh code/run_all.sh [wikitext.json] [ne_50m_admin_0_countries.geojson] [ne_10m_geography_marine_polys.geojson]
# The link coordinates and the Wikidata export are read from ../_data2/ (see 02_locate.py).
set -e
cd "$(dirname "$0")"
mkdir -p ../work
python3 01_parse.py "${1:-/mnt/user-data/uploads/Downloads/hist_wrecks_wikitext.json}"
python3 02_locate.py
python3 03_areas.py ${2:+"$2"} ${3:+"$3"}
python3 04_check_sample.py
python3 05_analyse.py
python3 build_site.py
python3 07_header.py
