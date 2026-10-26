"""Flag cells to one normalised 'flag group' per entry.

Wikipedia's lists show the flag (or naval ensign) the ship sailed under, as a template
such as {{flagcountry|UKGBI|civil}}, {{flag|Denmark}}, {{navy|German Empire}}, or as a
raw image link for city and small-state flags ([[File:Flag of Bremen.svg]] [[Bremen]]).

flag_country(raw) -> (country text as written, naval: bool)
flag_group(country) -> one of the groups below, merging states across eras.

The merges are the study's main judgement call, so they are all listed here:
  British   Kingdom of Great Britain, United Kingdom (UKGBI), Isle of Man, Jersey, Guernsey,
            British East India Company, Trinity House, HM Customs, RNLI, British Heligoland.
            Colonies and dominions (Canada, Newfoundland, Australia, India, Malta ...) are NOT
            merged: they go to Other.
  German    German Empire, Weimar Republic, Nazi Germany, Allied-occupied Germany, and before
            1871 Prussia, Hanover, the Hanseatic and other city states (Hamburg, Bremen, Lubeck,
            Rostock, Danzig, Stettin, Stralsund, Wismar, Greifswald, Elbing ...), Mecklenburg,
            Oldenburg, Holstein-Gottorp, the German Confederation.
  Dutch     Dutch Republic, Batavian Republic, Kingdom of Holland, United Kingdom of the
            Netherlands, Netherlands, Dutch East India Company.
  French    Kingdom of France, French Republics and Empires, Free France, Vichy France.
  Danish    Denmark, Denmark-Norway (to 1814), Faroe Islands.
  Norwegian Norway (separate flag in the lists from 1814, including the union years).
  Swedish   Sweden, United Kingdoms of Sweden and Norway when shown with the Swedish flag.
  Russian   Russian Empire, Russian SFSR, Soviet Union, Courland Governorate.
  Italian   Kingdom of Italy, Italian Social Republic, and before 1861 Sardinia (Savoy),
            Two Sicilies, Sicily, Tuscany, Papal States, Genoa, Venice, Lombardy-Venetia.
  Spanish, Portuguese, Greek (Kingdom, Republics), Ottoman/Turkish (Ottoman Empire, Turkey),
  Austrian (Habsburg monarchy, Austrian Empire, Austria-Hungary, Austria), American (United
  States, Confederate States, Republic of Texas), Finnish, Belgian, Irish (Kingdom of Ireland
  before 1801, Irish Free State and Ireland after 1922), Polish, Yugoslav, Romanian, Baltic
  states (Estonia, Latvia, Lithuania), and Other.
  Unknown   "Flag unknown" or an empty cell.
"""
import re

from wikitext import plain

TEMPLATE_RE = re.compile(r"\{\{\s*(#invoke:flag|flagcountry|flagicon image|flagicon|flagdeco|flagg|flagc|flagu|"
                         r"flag|navy|naval|army|air force|coast guard|listflag|country)\s*\|([^{}]*)\}\}", re.I)


def flag_country(raw):
    raw = raw or ""
    naval = False
    for m in TEMPLATE_RE.finditer(raw):
        name = m.group(1).lower()
        parts = [p.strip() for p in m.group(2).split("|")]
        pos = [p for p in parts if "=" not in p]
        if name in ("#invoke:flag", "flagg") and len(pos) >= 2:
            c = pos[1]
        elif name == "flagicon image":
            continue
        else:
            c = pos[0] if pos else ""
        if name in ("navy", "naval"):
            naval = True
        if name == "flagcountry" and len(pos) > 1 and pos[1].lower() in ("navy", "naval", "war"):
            naval = True
        if c:
            return c, naval
    # raw image flags: use the visible link text, falling back to the file name
    if re.search(r"navy|naval|war ensign|kriegsmarine|luftwaffe|admiralty", raw, re.I):
        naval = True
    txt = plain(raw)
    if not txt.strip():
        f = re.search(r"\[\[(?:File|Image):([^|\]]*)", raw, re.I)
        txt = f.group(1) if f else ""
    if re.search(r"\bunknown\b|unidentified", txt, re.I) and not re.search(r"\[\[File", raw, re.I):
        return "Flag unknown", False
    # keep the file name too, it often names the state (Flag of Bremen.svg)
    f = re.search(r"\[\[(?:File|Image):([^|\]]*)", raw, re.I)
    return (txt + (" | " + f.group(1) if f else "")).strip(), naval


GROUP_RULES = [
    ("Unknown", r"^(flag[s]? unknown|unknown|unidentified|\?|)$|^flag unknown"),
    ("British", r"^(UKGBI|UK|GBR|United Kingdom|United Kingdom of Great Britain and Ireland|Kingdom of Great Britain|Great Britain|"
                r"Isle of Man|Jersey|Guernsey|Bailiwick of (Jersey|Guernsey))$|Civil [Ee]nsign of the United Kingdom|"
                r"British East India Co|East India Company \(British|HM Customs|Trinity House|Royal National Lifeboat|British Heligoland|"
                r"Board of Trade|Customs|Royal Navy|Red Ensign|Blue Ensign"),
    ("Irish", r"^(Kingdom of\s+Ireland|Ireland|Irish Free State)$"),
    ("German", r"^(German Empire|Weimar Republic|Nazi Germany|Germany|Allied-occupied Germany|Prussia|Kingdom of Prussia|"
               r"Kingdom of Hanover|Electorate of Hanover|Hanover|Hamburg|Bremen|L[uü]beck|Mecklenburg|Oldenburg|Danzig|"
               r"German Confederation|North German Confederation|Free City of Danzig|Schleswig-Holstein)$|"
               r"Hamburg|Bremen|L[uü]beck|Rostock|Gda[nń]sk|Gdansk|Danzig|Szczecin|Stettin|Stralsund|Wismar|Greifswald|Elbl[aą]g|Elbing|"
               r"Ko[lł]obrzeg|Kolberg|S[lł]upsk|Stolp|Mecklenbur|Oldenburg|Holstein|Prussia|Memel|K[oö]nigsberg|Emden|East Frisia|"
               r"War Ensign of Germany|Kriegsmarine|Luftwaffe|Reichskriegsflagge|Germany|Anklam|Barth|Wolgast|Rügenwalde|Pillau|Hanover"),
    ("Dutch", r"^(Netherlands|Dutch Republic|Batavian Republic|Kingdom of Holland|United Kingdom of the Netherlands|"
              r"Kingdom of the Netherlands|Holland)$|Dutch East India|Statenvlag|Navy of the Dutch|Prinsenvlag|Netherlands"),
    ("French", r"^(France|FRA|Kingdom of France|Second French Empire|First French Empire|French First Republic|"
               r"French Second Republic|French Third Republic|Free France|Free French|Vichy France|July Monarchy)$|"
               r"Royaume de France|Flag of France|French"),
    ("Danish", r"^(Denmark|Denmark[-–]Norway|Faroe Islands|Danish West Indies)$|Danish|Dannebrog|Denmark"),
    ("Norwegian", r"^(Norway)$|Norge|Norwegian|Norway"),
    ("Swedish", r"^(Sweden|United Kingdoms of Sweden and Norway|Sweden[-–]Norway)$|Svensk flagg|Swedish|Sweden"),
    ("Russian", r"^(Russian Empire|Russia|Soviet Union|USSR|Russian SFSR|Tsardom of Russia)$|Russian|Courland|Soviet"),
    ("Finnish", r"^(Finland|Grand Duchy of Finland)$"),
    ("Italian", r"^(Kingdom of Italy|Italy|Italian Social Republic|Kingdom of Sardinia|Kingdom of the Two Sicilies|"
                r"Grand Duchy of Tuscany|Papal States|Republic of Genoa|Republic of Venice|Kingdom of Sicily|"
                r"Kingdom of Naples|Duchy of Parma|Duchy of Modena)$|Savoyard|Two Sicilies|Regno di Sicilia|Tuscan|Papal States|"
                r"Genoa|Genova|Venice|Venezia|Serene Republic|Lombardy|Italy|Italian|Sardinia|Livorno|Leghorn"),
    ("Spanish", r"^(Spain|Spanish Republic|Second Spanish Republic|Kingdom of Spain|Nationalist Spain|Francoist Spain)$|Spanish|Spain"),
    ("Portuguese", r"^(Portugal|Kingdom of Portugal)$|Portug"),
    ("Greek", r"^(Greece|Kingdom of Greece|First Hellenic Republic|Second Hellenic Republic|Ionian Islands|"
              r"United States of the Ionian Islands)$|Greek|Greece|Hellenic|Ionian"),
    ("Ottoman", r"^(Ottoman Empire|Turkey|Ottoman Tripolitania)$|Ottoman|Turkey|Turkish"),
    ("Austrian", r"^(Austria-Hungary|Austria[-–]Hungary|Austrian Empire|Austria|Habsburg Monarchy|Archduchy of Austria|Hungary)$|"
                 r"Austria|Habsburg|Trieste|Ragusa"),
    ("Belgian", r"^(Belgium|Austrian Netherlands)$|Belgi"),
    ("American", r"^(United States|USA|US|Confederate States of America|Republic of Texas|Texas)$|"
                 r"United States|Confederate|Revenue Cutter|Lighthouse Service|Coast and Geodetic"),
    ("Polish", r"^(Poland|Second Polish Republic)$"),
    ("Yugoslav", r"Yugoslav"),
    ("Romanian", r"Romania|United Principalities|Moldavia|Wallachia"),
    ("Baltic states", r"^(Estonia|Latvia|Lithuania)$"),
]
GROUP_RES = [(g, re.compile(p, re.I)) for g, p in GROUP_RULES]
# the order the groups are shown in, largest first overall (Other and Unknown last)
GROUP_ORDER = ["British", "German", "French", "Norwegian", "Dutch", "Swedish", "Danish", "Russian", "Italian",
               "Spanish", "Greek", "American", "Portuguese", "Belgian", "Austrian", "Ottoman", "Finnish", "Irish",
               "Polish", "Yugoslav", "Romanian", "Baltic states", "Other", "Unknown"]


def flag_group(country):
    c = (country or "").strip()
    head = c.split(" | ")[0].strip()
    for g, rx in GROUP_RES:
        if rx.search(head):
            return g
    for g, rx in GROUP_RES:
        if g != "Unknown" and rx.search(c):
            return g
    return "Other"
