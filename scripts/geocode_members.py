#!/usr/bin/env python3
"""Process MANTLE NETWORK members from Laposta, JSON, Excel or CSV.

The same processing pipeline supports both the scientific committee and the
member directory. Public output is a Jekyll-compatible CSV; review and keyword
reports may contain personal or operational data and should remain private.

Examples
--------
Retrieve members from a specified Laposta list:
    python scripts/geocode_members.py --laposta --list-name "YOUR LAPOSTA LIST NAME"

Process a saved snapshot:
    python scripts/geocode_members.py --input _data/private/committee/laposta_snapshot.json

Process a manual CSV/XLSX file:
    python scripts/geocode_members.py --input subscribers.xlsx

Disable keyword canonicalisation:
    python scripts/geocode_members.py --input subscribers.xlsx --no-standardize-keywords

Test without writing the public CSV:
    python scripts/geocode_members.py --laposta --list-name "YOUR LAPOSTA LIST NAME" --dry-run
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

OUTPUT_FIELDS = (
    "name", "institution", "country", "latitude", "longitude",
    "map_x", "map_y", "research_areas", "profile_url"
)
REVIEW_FIELDS = (
    "name", "email", "institution", "city_input", "city_matched",
    "country_input", "country_standardized", "country_code",
    "research_areas_input", "research_areas_standardized", "profile_url",
    "location_status", "location_note", "duplicate_email"
)

DEFAULT_LIST_NAME = "The MANTLE NETWORK Initiative - Scientific committee"
LAPOSTA_API_BASE = "https://api.laposta.org/v2"
LAPOSTA_CUSTOM_FIELDS = {
    "first_name": "firstname",
    "last_name": "lastname",
    "institution": "institution",
    "city": "city",
    "country": "country",
    "research_areas": "researchareas",
    "profile_url": "profileurl",
}

KEYWORD_ALIASES = {
    "Petrology": ["petrology", "petrologist", "petrologic", "petrological",
                  "mantle petrology", "igneous petrology", "igneous petroogy"],
    "Experimental petrology": ["experimental petrology", "experiments in petrology"],
    "Geochemistry": ["geochemistry", "geochemistrry", "geochem", "geochemical",
                     "mantle geochemistry"],
    "Mineral resources": ["mineral resources", "mineral deposits", "ore deposits",
                          "mantle-derived metal mineralization",
                          "mantle derived metal mineralization"],
    "Isotope geochemistry": ["isotope geochemistry", "isotopic geochemistry",
                             "radiogenic isotope", "radiogenic isotopes",
                             "radiogenic isotope geochemistry", "stable isotopes",
                             "non traditional stable isotopes",
                             "non-traditional stable isotopes",
                             "nontraditional stable isotopes"],
    "Geochronology": ["geochronology", "geochron"],
    "Geodynamics": ["geodynamics", "geodynamic"],
    "Geophysics": ["geophysics", "geophysical"],
    "Geophysical modelling": ["geophysical modelling", "geophysical modeling"],
    "Geodynamic modelling": ["geodynamic modelling", "geodynamic modeling"],
    "Mineralogy": ["mineralogy", "mineralogical"],
    "Abyssal peridotites": ["abyssal mantle", "abyssal mantle petrology",
                            "abyssal/ophiolitic mantle"],
    "Serpentinization and carbonation": ["serpentinization and carbonation",
                                         "serpentinization carbonation"],
    "Mantle dynamics": ["mantle dynamics", "deep-mantle dynamics",
                        "deep mantle dynamics"],
    "Mantle melting": ["mantle melting", "melting of the mantle"],
    "Magmatism": ["magmatism", "magmatic processes"],
    "Melt extraction": ["melt extraction", "magma extraction",
                        "melting and extraction", "magma melting and extraction"],
    "Ophiolites": ["ophiolite", "ophiolites", "ophiolitic"],
    "Orogenic peridotites": ["orogenic peridotite", "orogenic peridotites"],
    "Peridotites": ["peridotite", "peridotites"],
    "Mantle tectonics": ["mantle tectonic settings", "mantle tectonics"],
    "Lithosphere": ["lithosphere", "lithospheric"],
    "Lithosphere mapping": ["lithosphere mapping",
                            "3d cartography of the lithosphere",
                            "3d lithosphere mapping"],
    "Microanalysis": ["microanalysis", "micro-analysis",
                      "micro-analysis and analytical methods"],
    "Analytical methods": ["analytical methods", "analytical techniques"],
    "Rheology": ["rheology", "rock rheology", "rock deformation",
                 "deformation of rocks"],
    "Fluid–rock interactions": ["fluid-rock interactions",
                                "fluid rock interactions"],
    "Geology": ["geology", "engineering geology"],
    "Cartography": ["cartography", "mapping"],
}

COUNTRY_ALIASES = {
    "usa": "US", "u.s.a.": "US", "united states of america": "US",
    "united states": "US", "us": "US",
    "uk": "GB", "u.k.": "GB", "united kingdom": "GB", "great britain": "GB",
    "italia": "IT", "algérie": "DZ", "algerie": "DZ",
    "the netherlands": "NL", "netherlands": "NL",
    "netherlands (kingdom of the)": "NL", "holland": "NL",
    "czech republic": "CZ", "south korea": "KR", "north korea": "KP",
    "russia": "RU", "iran": "IR", "vietnam": "VN", "laos": "LA",
    "ivory coast": "CI", "côte d’ivoire": "CI", "côte d'ivoire": "CI",
    "democratic republic of the congo": "CD", "dr congo": "CD",
    "republic of the congo": "CG", "eswatini": "SZ", "swaziland": "SZ",
    "north macedonia": "MK", "macedonia": "MK", "palestine": "PS", "kosovo": "XK",
}
COUNTRY_CANONICAL_OVERRIDES = {
    "US": "United States", "GB": "United Kingdom", "IT": "Italy",
    "DZ": "Algeria", "NL": "Netherlands", "CZ": "Czechia",
    "KR": "South Korea", "KP": "North Korea", "RU": "Russia",
    "CI": "Côte d’Ivoire", "CD": "Democratic Republic of the Congo",
    "CG": "Republic of the Congo", "MK": "North Macedonia",
}
CITY_ALIASES = {
    ("alger", "DZ"): "Algiers", ("genova", "IT"): "Genoa",
    ("milano", "IT"): "Milan", ("munster", "DE"): "Münster",
    ("cambridge", "GB"): "Cambridge", ("zurich", "CH"): "Zürich",
    ("washington dc", "US"): "Washington",
    ("higashi hiroshima", "JP"): "Higashihiroshima",
    ("cologne", "DE"): "Köln",
}


def plain(value):
    return "" if value is None else str(value).strip()


def norm(value):
    value = plain(value).casefold().replace("’", "'")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE).split())


def title_case_words(value):
    return " ".join(word.capitalize() for word in plain(value).split())


def load_country_reference(path):
    names, canonical = {}, {}
    if not path or not Path(path).exists():
        return names, canonical
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 16:
                continue
            code, country = cols[0].upper(), cols[4].strip()
            names[norm(country)] = code
            canonical[code] = country
            for alias in cols[3].split(","):
                if alias.strip():
                    names[norm(alias)] = code
    for alias, code in COUNTRY_ALIASES.items():
        names[norm(alias)] = code
    return names, canonical


def canonical_country(value, country_names, canonical_names):
    raw, key = plain(value), norm(value)
    code = COUNTRY_ALIASES.get(key) or country_names.get(key)
    if not code and len(key) == 2 and key.isalpha():
        code = key.upper()
    if not code:
        return raw, "", "unrecognized country"
    return COUNTRY_CANONICAL_OVERRIDES.get(code, canonical_names.get(code, raw)), code, ""


def load_gazetteer(path):
    by_country, by_city = defaultdict(list), defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 19:
                continue
            try:
                lat, lon, pop = float(cols[4]), float(cols[5]), int(cols[14] or 0)
            except ValueError:
                continue
            item = {"name": cols[1], "ascii": cols[2], "lat": lat,
                    "lon": lon, "cc": cols[8].upper(), "population": pop}
            for n in {norm(cols[1]), norm(cols[2])}:
                if n:
                    by_country[(n, item["cc"])].append(item)
                    by_city[n].append(item)
    for index in (by_country, by_city):
        for key in index:
            index[key].sort(key=lambda x: x["population"], reverse=True)
    return by_country, by_city


def lookup_city(city, country_code, indexes):
    by_country, by_city = indexes
    raw = plain(city)
    if not raw:
        return None, "missing city"
    key = norm(raw)
    alias = CITY_ALIASES.get((key, country_code))
    if alias:
        key = norm(alias)
    if country_code:
        candidates = by_country.get((key, country_code), [])
        if candidates:
            return candidates[0], "matched city and country"
    candidates = by_city.get(key, [])
    if not candidates:
        return None, f"city '{raw}' not found"
    countries = {x["cc"] for x in candidates}
    if country_code and country_code not in countries:
        return None, f"city found, but not in specified country ({country_code})"
    if len(countries) > 1:
        return None, "ambiguous city; country could not disambiguate"
    return candidates[0], "matched city; country name/code needs review"


def keyword_canonical_map():
    mapping = {}
    for canonical, aliases in KEYWORD_ALIASES.items():
        mapping[norm(canonical)] = canonical
        for alias in aliases:
            mapping[norm(alias)] = canonical
    return mapping


def standardize_keywords(value, mapping):
    raw = plain(value)
    if not raw:
        return [], []
    parts = re.split(r"[;,\n|.!?]+", raw)
    found, unknown = [], []
    aliases = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)
    for part in parts:
        term = part.strip(" .:-")
        if not term:
            continue
        key = norm(term)
        if key in mapping:
            canonical = mapping[key]
            if canonical not in found:
                found.append(canonical)
            continue
        key = key.replace("pertology", "petrology").replace(
            "geochemistrry", "geochemistry").replace(
            "igneous petroogy", "igneous petrology")
        matched_targets, remainder = [], key
        for alias_key, target in aliases:
            if len(alias_key) < 4:
                continue
            pattern = r"(?<!\w)" + re.escape(alias_key) + r"(?!\w)"
            if re.search(pattern, remainder):
                if target not in matched_targets:
                    matched_targets.append(target)
                remainder = re.sub(pattern, " ", remainder)
        remainder = re.sub(
            r"\b(and|or|of|the|in|for|with|on|related to)\b", " ", remainder)
        remainder = " ".join(remainder.split()).strip(" -/:,")
        if matched_targets and len(remainder) > 2:
            cleaned = title_case_words(term)
            if cleaned not in unknown and cleaned not in found:
                unknown.append(cleaned)
            continue
        for target in matched_targets:
            if target not in found:
                found.append(target)
        if len(remainder) > 2:
            cleaned = title_case_words(remainder)
            if cleaned not in unknown and cleaned not in found:
                unknown.append(cleaned)
    for term in unknown:
        if term not in found:
            found.append(term)
    deduplicated, seen = [], set()
    for term in found:
        canonical = title_case_words(mapping.get(norm(term), term))
        if norm(canonical) not in seen:
            deduplicated.append(canonical)
            seen.add(norm(canonical))
    deduplicated_unknown, seen_unknown = [], set()
    for term in unknown:
        if norm(term) not in seen_unknown:
            deduplicated_unknown.append(title_case_words(term))
            seen_unknown.add(norm(term))
    return deduplicated, deduplicated_unknown


def build_projector():
    def natural_earth1(lon, lat):
        lam = math.radians(lon)
        phi = max(-math.pi / 2, min(math.pi / 2, math.radians(lat)))
        p2, p4 = phi * phi, phi ** 4
        x = lam * (0.8707 - 0.131979*p2 + p4*(-0.013791 + p4*(0.003971 - 0.001529*p2)))
        y = phi * (1.007226 + p2*(0.015085 + p4*(-0.044475 + 0.028874*p2 - 0.005916*p4)))
        return x, y
    def project(lat, lon):
        x, y = natural_earth1(lon, lat)
        return round(600 + 218*x, 2), round(310 - 218*y, 2)
    return project


def _laposta_get(session, endpoint, params=None):
    url = f"{LAPOSTA_API_BASE}/{endpoint.lstrip('/')}"
    for attempt in range(5):
        try:
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt == 4:
                    response.raise_for_status()
                wait = response.headers.get("Retry-After")
                time.sleep(float(wait) if wait else min(2 ** attempt, 30))
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError(f"Unexpected Laposta response from {endpoint}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            if attempt == 4:
                raise RuntimeError(f"Laposta API request failed ({endpoint}): {exc}") from exc
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"Laposta API request failed ({endpoint})")


def laposta_members(list_name, state="active"):
    api_key = os.environ.get("LAPOSTA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("LAPOSTA_API_KEY environment variable is not set.")
    session = requests.Session()
    session.auth = HTTPBasicAuth(api_key, "")
    session.headers.update({"Accept": "application/json"})

    lists_payload = _laposta_get(session, "list")
    lists = lists_payload.get("data", [])
    matches = []
    for entry in lists:
        obj = entry.get("list", entry) if isinstance(entry, dict) else {}
        if obj.get("name") == list_name:
            matches.append(obj)
    if len(matches) != 1:
        available = [((x.get("list", x)).get("name", "")) for x in lists if isinstance(x, dict)]
        raise RuntimeError(
            f"Expected exactly one Laposta list named {list_name!r}; "
            f"found {len(matches)}. Available lists: {available}"
        )
    selected = matches[0]
    list_id = selected.get("list_id")
    if not list_id:
        raise RuntimeError("Laposta list response did not include list_id.")

    members, cursor, seen = [], None, set()
    while True:
        params = {"list_id": list_id, "limit": 1000}
        if state != "all":
            params["state"] = state
        if cursor:
            if cursor in seen:
                raise RuntimeError("Laposta returned a repeated pagination cursor.")
            seen.add(cursor)
            params["cursor"] = cursor
        payload = _laposta_get(session, "member", params)
        page = payload.get("data", [])
        for entry in page:
            obj = entry.get("member", entry) if isinstance(entry, dict) else {}
            if obj:
                members.append(obj)
        pagination = payload.get("pagination") or {}
        if not pagination.get("has_more"):
            break
        cursor = pagination.get("next_cursor")
        if not cursor:
            raise RuntimeError("Laposta pagination missing next_cursor.")

    rows = []
    for member in members:
        custom = member.get("custom_fields") or {}
        row = {
            "Email": member.get("email", ""),
            "First name": custom.get("firstname", ""),
            "Last name": custom.get("lastname", ""),
            "Institution": custom.get("institution", ""),
            "City": custom.get("city", ""),
            "Country": custom.get("country", ""),
            "Research areas": custom.get("researchareas", ""),
            "Profile URL": custom.get("profileurl", ""),
        }
        rows.append(row)
    metadata = {
        "source": "Laposta API",
        "list_name": selected.get("name", list_name),
        "list_id": list_id,
        "member_state_filter": state,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(rows),
    }
    return rows, metadata


def write_snapshot(path, rows, metadata):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(
        {"metadata": metadata, "members": rows},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("members", payload.get("data", []))
    rows = []
    for item in records:
        if isinstance(item, dict) and isinstance(item.get("member"), dict):
            item = item["member"]
        if not isinstance(item, dict):
            continue
        custom = item.get("custom_fields") or {}
        rows.append({
            "Email": item.get("Email", item.get("email", "")),
            "First name": item.get("First name", item.get("first_name", custom.get("firstname", ""))),
            "Last name": item.get("Last name", item.get("last_name", custom.get("lastname", ""))),
            "Institution": item.get("Institution", item.get("institution", custom.get("institution", ""))),
            "City": item.get("City", item.get("city", custom.get("city", ""))),
            "Country": item.get("Country", item.get("country", custom.get("country", ""))),
            "Research areas": item.get("Research areas", item.get("research_areas", custom.get("researchareas", ""))),
            "Profile URL": item.get("Profile URL", item.get("profile_url", custom.get("profileurl", ""))),
        })
    return rows


def read_source(path, sheet):
    path = Path(path)
    if path.suffix.lower() == ".json":
        return read_json(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            sys.exit("Reading .xlsx requires openpyxl: pip install openpyxl")
        wb = load_workbook(path, read_only=True, data_only=True)
        if sheet not in wb.sheetnames:
            sys.exit(f"Sheet '{sheet}' not found. Available: {', '.join(wb.sheetnames)}")
        ws = wb[sheet]
        rows = ws.iter_rows(values_only=True)
        headers = [plain(x) for x in next(rows)]
        return [dict(zip(headers, row)) for row in rows
                if any(x is not None for x in row)]
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get(row, *keys):
    normalized = {norm(k): v for k, v in row.items() if k is not None}
    for key in keys:
        if norm(key) in normalized:
            return plain(normalized[norm(key)])
    return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--laposta", action="store_true",
                              help="retrieve members directly from Laposta")
    source_group.add_argument("--input", help="input JSON, XLSX or CSV")
    parser.add_argument("--sheet", default="Subscribers")
    parser.add_argument("--list-name", default=DEFAULT_LIST_NAME)
    parser.add_argument("--member-state", default="active",
                        choices=("active", "unsubscribed", "bounced", "all"))
    parser.add_argument("--snapshot", default="",
                        help="optional private JSON snapshot path (Laposta mode)")
    parser.add_argument("--gazetteer", default="_data/reference/cities1000.txt")
    parser.add_argument("--country-info", default="")
    parser.add_argument("--output", default="_data/committee_members.csv")
    parser.add_argument("--review", default="_data/private/committee/committee_review.csv")
    parser.add_argument("--keywords", default="_data/private/committee/committee_keywords.csv")
    parser.add_argument("--include-unresolved", action="store_true")
    parser.add_argument("--no-standardize-keywords", action="store_true",
                        help="retain submitted research-area text without canonicalisation")
    parser.add_argument("--dry-run", action="store_true",
                        help="process and report, but do not write the public map CSV")
    parser.add_argument("--min-members", type=int, default=1,
                        help="abort if fewer source rows are retrieved (safety guard)")
    parser.add_argument("--max-drop-fraction", type=float, default=0.5,
                        help="abort if resolved/nonduplicate map rows fall below this fraction of prior output")
    args = parser.parse_args()

    if args.laposta:
        try:
            rows, metadata = laposta_members(args.list_name, args.member_state)
        except Exception as exc:
            sys.exit(f"Laposta error: {exc}")
        if len(rows) < args.min_members:
            sys.exit(f"Safety check failed: retrieved {len(rows)} rows; minimum is {args.min_members}.")
        if args.snapshot:
            write_snapshot(args.snapshot, rows, metadata)
            print(f"Private snapshot: {args.snapshot}")
    else:
        source = Path(args.input)
        if not source.exists():
            sys.exit(f"Input file not found: {source}")
        rows = read_source(source, args.sheet)

    gazetteer_path = Path(args.gazetteer)
    if not gazetteer_path.exists():
        sys.exit(f"GeoNames gazetteer not found: {gazetteer_path}")
    country_info = Path(args.country_info) if args.country_info else gazetteer_path.with_name("countryInfo.txt")
    country_names, canonical_names = load_country_reference(country_info)
    gazetteer = load_gazetteer(gazetteer_path)
    projector = build_projector()
    keyword_map = keyword_canonical_map() if not args.no_standardize_keywords else {}
    email_counts = Counter(get(r, "Email", "email").casefold()
                           for r in rows if get(r, "Email", "email"))
    seen_emails, website_rows, review_rows = set(), [], []
    keyword_counts, unknown_counts = Counter(), Counter()

    for row in rows:
        first = get(row, "First name", "first_name")
        last = get(row, "Last name", "last_name")
        name = title_case_words(get(row, "Name", "name") or
                                " ".join(x for x in (first, last) if x))
        sort_last_name = title_case_words(last or (name.split()[-1] if name else ""))
        email = get(row, "Email", "email").casefold()
        institution = get(row, "Institution", "institution")
        city_input = get(row, "City", "city")
        country_input = get(row, "Country", "country")
        profile_url = get(row, "Profile URL", "profile_url")
        research_input = get(row, "Research areas", "research_areas", "Keywords", "keywords")

        if args.no_standardize_keywords:
            keywords = [plain(x) for x in re.split(r"[;\n|]+", research_input) if plain(x)]
            unknown = []
        else:
            keywords, unknown = standardize_keywords(research_input, keyword_map)
        keyword_counts.update(keywords)
        unknown_counts.update(unknown)

        duplicate = bool(email and email in seen_emails)
        if email:
            seen_emails.add(email)
        country_std, cc, country_note = canonical_country(country_input, country_names, canonical_names)
        city_result, city_note = lookup_city(city_input, cc, gazetteer)
        location_status = "resolved" if city_result else "unresolved"
        notes = "; ".join(x for x in (country_note, city_note) if x)
        if city_result and cc and city_result["cc"] != cc:
            location_status = "review"
            notes += "; gazetteer country differs from input"
        if not cc:
            location_status = "review"
        if duplicate:
            notes = (notes + "; duplicate email (later occurrence)").strip("; ")

        if city_result and (not cc or city_result["cc"] == cc) and not duplicate:
            x, y = projector(city_result["lat"], city_result["lon"])
            website_rows.append({
                "name": name, "_sort_last_name": sort_last_name,
                "institution": institution, "country": country_std,
                "latitude": f"{city_result['lat']:.5f}",
                "longitude": f"{city_result['lon']:.5f}",
                "map_x": f"{x:.2f}", "map_y": f"{y:.2f}",
                "research_areas": "; ".join(keywords), "profile_url": profile_url,
            })
        elif args.include_unresolved and not duplicate:
            website_rows.append({
                "name": name, "_sort_last_name": sort_last_name,
                "institution": institution, "country": country_std,
                "latitude": "", "longitude": "", "map_x": "", "map_y": "",
                "research_areas": "; ".join(keywords), "profile_url": profile_url,
            })

        review_rows.append({
            "name": name, "_sort_last_name": sort_last_name, "email": email,
            "institution": institution, "city_input": city_input,
            "city_matched": city_result["name"] if city_result else "",
            "country_input": country_input, "country_standardized": country_std,
            "country_code": cc, "research_areas_input": research_input,
            "research_areas_standardized": "; ".join(keywords),
            "profile_url": profile_url, "location_status": location_status,
            "location_note": notes, "duplicate_email": "yes" if duplicate else "no",
        })

    for output_rows in (website_rows, review_rows):
        output_rows.sort(key=lambda r: (r["_sort_last_name"].casefold(), r["name"].casefold()))
        for output_row in output_rows:
            output_row.pop("_sort_last_name", None)

    unresolved = sum(r["location_status"] != "resolved" for r in review_rows)
    duplicates = sum(r["duplicate_email"] == "yes" for r in review_rows)
    print(f"Source rows: {len(rows)}")
    print(f"Website rows: {len(website_rows)}")
    print(f"Locations needing review/unresolved: {unresolved}")
    print(f"Duplicate email rows flagged: {duplicates}")

    if args.dry_run:
        print("Dry run: no output files written.")
        return

    # Protect against an unexpectedly large reduction in public map records.
    output_path = Path(args.output)
    if output_path.exists() and not args.include_unresolved:
        try:
            with output_path.open(encoding="utf-8-sig", newline="") as f:
                previous_count = max(0, sum(1 for _ in csv.DictReader(f)))
            if previous_count and len(website_rows) < previous_count * (1 - args.max_drop_fraction):
                sys.exit(
                    f"Safety check failed: new map has {len(website_rows)} rows versus "
                    f"{previous_count} previously. Inspect inputs/geocoding before publishing. "
                    "Override with --max-drop-fraction 1.0 if intentional."
                )
        except (OSError, csv.Error):
            sys.exit("Could not validate existing output CSV; refusing to overwrite.")

    def write_csv(path, fields, data, encoding="utf-8-sig"):
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)

    if not args.dry_run:
        write_csv(args.output, OUTPUT_FIELDS, website_rows, encoding="utf-8")
        write_csv(args.review, REVIEW_FIELDS, review_rows)
        write_csv(args.keywords, ["keyword", "count", "controlled_term"], [
            {"keyword": term, "count": count,
             "controlled_term": "yes" if norm(term) in keyword_map else "review"}
            for term, count in sorted(keyword_counts.items(),
                                      key=lambda x: (-x[1], x[0].casefold()))
        ])
    print(f"Website CSV: {args.output}")
    print(f"Review CSV: {args.review}")
    print(f"Keyword inventory: {args.keywords}")
    print("Review reports before publishing.")


if __name__ == "__main__":
    main()
