#!/usr/bin/env python3
"""
Build the MANTLE NETWORK website member map directly from a mailing-list export.

Reads an Excel workbook (default sheet: Subscribers) or CSV, standardizes fields,
canonicalizes countries/cities and research keywords, geocodes offline with GeoNames,
and writes:
  1. website-ready map CSV (same columns as the existing Jekyll map)
  2. review CSV with one row per subscriber, including unresolved locations
  3. keyword inventory CSV for maintaining a consistent controlled vocabulary


Dependencies: openpyxl (for .xlsx input); standard library otherwise.
"""

import argparse
import csv
import math
import re
import sys
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

OUTPUT_FIELDS = (
    "name", "institution", "country", "latitude", "longitude",
    "map_x", "map_y", "research_areas", "profile_url"
)
REVIEW_FIELDS = (
    "name", "email", "institution", "city_input", "city_matched",
    "country_input", "country_standardized", "country_code",
    "research_areas_input",
    "research_areas_standardized", "profile_url", "location_status",
    "location_note", "duplicate_email"
)

# Standard keyword -> variants. Keep this list deliberately editable.
KEYWORD_ALIASES = {
    "Petrology": ["petrology", "petrologist", "petrologic", "petrological",
                  "mantle petrology", "igneous petrology", "igneous petroogy"],
    "Experimental petrology": ["experimental petrology", "experiments in petrology"],
    "Geochemistry": ["geochemistry", "geochemistrry", "geochem", "geochemical",
                     "mantle geochemistry"],
    "Mineral resources": [
        "mineral resources", "mineral deposits", "ore deposits",
        "mantle-derived metal mineralization",
        "mantle derived metal mineralization",
    ],
    "Isotope geochemistry": [
        "isotope geochemistry", "isotopic geochemistry",
        "radiogenic isotope", "radiogenic isotopes",
        "radiogenic isotope geochemistry",
        "stable isotopes", "non traditional stable isotopes",
        "non-traditional stable isotopes", "nontraditional stable isotopes",
    ],
    "Geochronology": ["geochronology", "geochron"],
    "Geodynamics": ["geodynamics", "geodynamic"],
    "Geophysics": ["geophysics", "geophysical"],
    "Geophysical modelling": ["geophysical modelling", "geophysical modeling",
                              "geophysical modelling"],
    "Geodynamic modelling": ["geodynamic modelling", "geodynamic modeling"],
    "Mineralogy": ["mineralogy", "mineralogical"],
    "Abyssal peridotites": ["abyssal mantle", "abyssal mantle petrology", "abyssal/ophiolitic mantle"],
    "Serpentinization and carbonation": ["serpentinization and carbonation", "serpentinization carbonation"],
    "Mantle dynamics": ["mantle dynamics", "deep-mantle dynamics", "deep mantle dynamics"],
    "Mantle melting": ["mantle melting", "melting of the mantle"],
    "Magmatism": ["magmatism", "magmatic processes"],
    "Melt extraction": ["melt extraction", "magma extraction", "melting and extraction",
                        "magma melting and extraction"],
    "Ophiolites": ["ophiolite", "ophiolites", "ophiolitic"],
    "Orogenic peridotites": ["orogenic peridotite", "orogenic peridotites"],
    "Peridotites": ["peridotite", "peridotites"],
    "Mantle tectonics": ["mantle tectonic settings", "mantle tectonics"],
    "Lithosphere": ["lithosphere", "lithospheric"],
    "Lithosphere mapping": ["lithosphere mapping", "3d cartography of the lithosphere",
                            "3d lithosphere mapping"],
    "Microanalysis": ["microanalysis", "micro-analysis", "micro-analysis and analytical methods"],
    "Analytical methods": ["analytical methods", "analytical techniques"],
    "Rheology": ["rheology", "rock rheology", "rock deformation",
                 "deformation of rocks"],
    "Fluid–rock interactions": ["fluid-rock interactions", "fluid rock interactions"],
    "Geology": ["geology", "engineering geology"],
    "Cartography": ["cartography", "mapping"],
}

COUNTRY_ALIASES = {
    "usa": "US", "u.s.a.": "US", "united states of america": "US",
    "united states": "US", "us": "US",
    "uk": "GB", "u.k.": "GB", "united kingdom": "GB", "great britain": "GB",
    "italia": "IT", "algérie": "DZ", "algerie": "DZ",
    "the netherlands": "NL", "netherlands": "NL", "netherlands (kingdom of the)": "NL", "holland": "NL",
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
    ("alger", "DZ"): "Algiers",
    ("genova", "IT"): "Genoa",
    ("milano", "IT"): "Milan",
    ("munster", "DE"): "Münster",
    ("cambridge", "GB"): "Cambridge",
    ("zurich", "CH"): "Zürich",
    ("washington dc", "US"): "Washington",
    ("higashi hiroshima", "JP"): "Higashihiroshima",
    ("cologne", "DE"): "Köln",
}

def plain(value):
    if value is None:
        return ""
    return str(value).strip()

def norm(value):
    value = plain(value).casefold().replace("’", "'")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE).split())

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
    raw = plain(value)
    key = norm(raw)
    code = COUNTRY_ALIASES.get(key) or country_names.get(key)
    if not code and len(key) == 2 and key.isalpha():
        code = key.upper()
    if not code:
        return raw, "", "unrecognized country"
    display = COUNTRY_CANONICAL_OVERRIDES.get(code, canonical_names.get(code, raw))
    return display, code, ""

def load_gazetteer(path):
    by_country, by_city = defaultdict(list), defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 19:
                continue
            try:
                lat, lon = float(cols[4]), float(cols[5])
                pop = int(cols[14] or 0)
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
    """Map free-text interests to controlled terms while preserving useful unknown terms.

    Split on common list separators and sentence boundaries. Then extract known
    terms from phrases such as "petrology and geochemistry". Any remaining
    meaningful text is retained as a reviewable keyword rather than discarded.
    """
    raw = plain(value)
    if not raw:
        return [], []

    # Sentence boundaries are useful in long free-text responses. Commas and
    # semicolons are treated as separators because the form commonly uses them
    # to enumerate interests.
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

        # Correct common spelling variants before extracting terms.
        key = key.replace("pertology", "petrology").replace("geochemistrry", "geochemistry")
        key = key.replace("igneous petroogy", "igneous petrology")
        matched_targets = []
        remainder = key
        for alias_key, target in aliases:
            if len(alias_key) < 4:
                continue
            pattern = r"(?<!\w)" + re.escape(alias_key) + r"(?!\w)"
            if re.search(pattern, remainder):
                if target not in matched_targets:
                    matched_targets.append(target)
                remainder = re.sub(pattern, " ", remainder)

        for target in matched_targets:
            if target not in found:
                found.append(target)

        remainder = re.sub(r"\b(and|or|of|the|in|for|with|on|and|related to)\b", " ", remainder)
        remainder = " ".join(remainder.split()).strip(" -/:,")
        if len(remainder) > 2:
            # Preserve unknown scientific concepts in readable form for review.
            cleaned = " ".join(word.capitalize() for word in remainder.split())
            if cleaned not in unknown and cleaned not in found:
                unknown.append(cleaned)

    for term in unknown:
        if term not in found:
            found.append(term)

    # Final case/whitespace-insensitive deduplication. This prevents variants
    # such as "Experimental petrology" and "experimental petrology " from
    # appearing as separate output categories.
    deduplicated = []
    seen = set()
    for term in found:
        key = norm(term)
        canonical = mapping.get(key, term)
        canonical_key = norm(canonical)
        if canonical_key not in seen:
            deduplicated.append(canonical)
            seen.add(canonical_key)

    deduplicated_unknown = []
    seen_unknown = set()
    for term in unknown:
        key = norm(term)
        if key not in seen_unknown:
            deduplicated_unknown.append(term)
            seen_unknown.add(key)

    return deduplicated, deduplicated_unknown

def build_projector():
    def natural_earth1(lon, lat):
        lam, phi = math.radians(lon), max(-math.pi/2, min(math.pi/2, math.radians(lat)))
        p2, p4 = phi*phi, phi**4
        x = lam * (0.8707 - 0.131979*p2 + p4*(-0.013791 + p4*(0.003971 - 0.001529*p2)))
        y = phi * (1.007226 + p2*(0.015085 + p4*(-0.044475 + 0.028874*p2 - 0.005916*p4)))
        return x, y
    def project(lat, lon):
        x, y = natural_earth1(lon, lat)
        return round(600 + 218*x, 2), round(310 - 218*y, 2)
    return project

def read_source(path, sheet):
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            sys.exit("Reading .xlsx requires openpyxl: pip install openpyxl")
        wb = load_workbook(path, read_only=True, data_only=True)
        if sheet not in wb.sheetnames:
            sys.exit(f"Sheet '{sheet}' not found. Available sheets: {', '.join(wb.sheetnames)}")
        ws = wb[sheet]
        rows = ws.iter_rows(values_only=True)
        headers = [plain(x) for x in next(rows)]
        return [dict(zip(headers, row)) for row in rows if any(x is not None for x in row)]
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
    parser.add_argument("input", help="Mailing-list .xlsx export or CSV")
    parser.add_argument("--sheet", default="Subscribers", help="Excel sheet (default: Subscribers)")
    parser.add_argument("--gazetteer", required=True, help="GeoNames cities1000.txt")
    parser.add_argument("--country-info", help="GeoNames countryInfo.txt (default: next to gazetteer)")
    parser.add_argument("--output", default="members.csv", help="website-ready map CSV")
    parser.add_argument("--review", default="members_review.csv", help="normalization and geocoding audit CSV")
    parser.add_argument("--keywords", default="keyword_inventory.csv", help="keyword inventory CSV")
    parser.add_argument("--include-unresolved", action="store_true",
                        help="include unresolved members in website CSV with blank coordinates (default: omit)")
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        sys.exit(f"Input file not found: {source}")
    gazetteer_path = Path(args.gazetteer)
    if not gazetteer_path.exists():
        sys.exit(f"GeoNames gazetteer not found: {gazetteer_path}")
    country_info = Path(args.country_info) if args.country_info else gazetteer_path.with_name("countryInfo.txt")
    country_names, canonical_names = load_country_reference(country_info)
    gazetteer = load_gazetteer(gazetteer_path)
    projector = build_projector()
    keyword_map = keyword_canonical_map()
    rows = read_source(source, args.sheet)

    # Email-based deduplication: retain first occurrence and flag later duplicates in review.
    email_counts = Counter(get(r, "Email", "email").casefold() for r in rows if get(r, "Email", "email"))
    seen_emails = set()
    website_rows, review_rows = [], []
    keyword_counts = Counter()
    unknown_counts = Counter()

    for row in rows:
        first = get(row, "First name", "first_name")
        last = get(row, "Last name", "last_name")
        name = get(row, "Name", "name") or " ".join(x for x in (first, last) if x)
        email = get(row, "Email", "email").casefold()
        institution = get(row, "Institution", "institution")
        city_input = get(row, "City", "city")
        country_input = get(row, "Country", "country")
        profile_url = get(row, "Profile URL", "profile_url")
        research_input = get(row, "Research areas", "research_areas", "Keywords", "keywords")
        country_std, cc, country_note = canonical_country(country_input, country_names, canonical_names)
        city_result, city_note = lookup_city(city_input, cc, gazetteer)
        keywords, unknown = standardize_keywords(research_input, keyword_map)
        keyword_counts.update(keywords)
        unknown_counts.update(unknown)
        duplicate = bool(email and email in seen_emails)
        if email:
            seen_emails.add(email)

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
                "name": name, "institution": institution, "country": country_std,
                "latitude": f"{city_result['lat']:.5f}", "longitude": f"{city_result['lon']:.5f}",
                "map_x": f"{x:.2f}", "map_y": f"{y:.2f}",
                "research_areas": "; ".join(keywords), "profile_url": profile_url,
            })
        elif args.include_unresolved and not duplicate:
            website_rows.append({
                "name": name, "institution": institution, "country": country_std,
                "latitude": "", "longitude": "", "map_x": "", "map_y": "",
                "research_areas": "; ".join(keywords), "profile_url": profile_url,
            })

        review_rows.append({
            "name": name, "email": email, "institution": institution,
            "city_input": city_input, "city_matched": city_result["name"] if city_result else "",
            "country_input": country_input, "country_standardized": country_std,
            "country_code": cc,
            "research_areas_input": research_input, "research_areas_standardized": "; ".join(keywords),
            "profile_url": profile_url, "location_status": location_status,
            "location_note": notes, "duplicate_email": "yes" if duplicate else "no",
        })

    def write_csv(path, fields, data, *, encoding="utf-8-sig"):
        """Write a CSV, allowing UTF-8 without BOM where strict headers matter."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)

    # Jekyll reads this file as structured data. Write plain UTF-8 (no BOM)
    # so the first header is exactly "name", not "\\ufeffname".
    write_csv(args.output, OUTPUT_FIELDS, website_rows, encoding="utf-8")
    # Keep BOM on the review/report CSVs for convenient opening in spreadsheet apps.
    write_csv(args.review, REVIEW_FIELDS, review_rows)
    write_csv(args.keywords, ["keyword", "count", "controlled_term"], [
        {"keyword": term, "count": count, "controlled_term": "yes" if norm(term) in keyword_map else "review"}
        for term, count in sorted(keyword_counts.items(), key=lambda x: (-x[1], x[0].casefold()))
    ])
    unresolved = sum(r["location_status"] != "resolved" for r in review_rows)
    duplicates = sum(r["duplicate_email"] == "yes" for r in review_rows)
    print(f"Source rows: {len(rows)}")
    print(f"Website rows written: {len(website_rows)}")
    print(f"Locations needing review/unresolved: {unresolved}")
    print(f"Duplicate email rows flagged: {duplicates}")
    print(f"Website CSV: {args.output}")
    print(f"Review CSV: {args.review}")
    print(f"Keyword inventory: {args.keywords}")
    print("Review members_review.csv before publishing.")

if __name__ == "__main__":
    main()
