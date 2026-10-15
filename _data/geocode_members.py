#!/usr/bin/env python3
"""Convert a city-based MANTLE NETWORK members CSV into the map CSV.

Input CSV columns (header names are case-sensitive):
    name,institution,country,city,research_areas,profile_url

Output CSV columns:
    name,institution,country,latitude,longitude,map_x,map_y,research_areas,profile_url

Location lookup is offline and uses GeoNames' `cities1000.txt` gazetteer.
Download it from https://download.geonames.org/export/dump/cities1000.zip,
unzip it, and pass the extracted `cities1000.txt` with --gazetteer. Also download
https://download.geonames.org/export/dump/countryInfo.txt into the same folder
so full country names can be matched reliably.

Dependencies:
    No additional Python packages are required.

Example:
    python geocode_members.py members_input.csv members.csv \\
        --gazetteer data/cities1000.txt

The map coordinates use D3 geoNaturalEarth1 equations and a 1200 x 620 SVG canvas.
MAP_PADDING controls the fit to the map artwork.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Must match the SVG viewBox in _includes/interactive-map.html.
MAP_WIDTH = 1200.0
MAP_HEIGHT = 620.0
MAP_PADDING = 18.0

INPUT_REQUIRED = ("name", "institution", "country", "city", "research_areas", "profile_url")
OUTPUT_FIELDS = (
    "name", "institution", "country", "latitude", "longitude",
    "map_x", "map_y", "research_areas", "profile_url"
)

# GeoNames countryInfo.txt is not required: country names are matched against
# the country column in cities1000.txt (ISO-2 code). This built-in map covers
# common cases; extend it if your CSV uses another country-name spelling.
COUNTRY_ALIASES = {
    "united states": "US", "usa": "US", "u.s.a.": "US", "united states of america": "US",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "russia": "RU", "south korea": "KR", "north korea": "KP",
    "iran": "IR", "vietnam": "VN", "laos": "LA", "moldova": "MD",
    "bolivia": "BO", "venezuela": "VE", "tanzania": "TZ", "syria": "SY",
    "brunei": "BN", "taiwan": "TW", "ivory coast": "CI", "côte d’ivoire": "CI",
    "cote d'ivoire": "CI", "democratic republic of the congo": "CD",
    "dr congo": "CD", "republic of the congo": "CG", "congo": "CG",
    "czech republic": "CZ", "czechia": "CZ", "the netherlands": "NL",
    "netherlands": "NL", "the gambia": "GM", "gambia": "GM",
    "eswatini": "SZ", "swaziland": "SZ", "macedonia": "MK", "north macedonia": "MK",
    "palestine": "PS", "kosovo": "XK",
}


def norm(value):
    return " ".join((value or "").strip().casefold().replace("’", "'").split())


def country_code(country, country_names=None):
    value = norm(country)
    if value in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[value]
    if country_names and value in country_names:
        return country_names[value]
    # Allow ISO-2 country codes as input.
    if len(value) == 2 and value.isalpha():
        return value.upper()
    return None


def load_country_names(path):
    """Read GeoNames countryInfo.txt and map country names to ISO-2 codes."""
    names = {}
    if not path or not Path(path).exists():
        return names
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            code, country_name = cols[0].upper(), cols[4]
            names[norm(country_name)] = code
            # GeoNames sometimes includes comma-separated alternate country names.
            if len(cols) > 3:
                for alias in cols[3].split(","):
                    if alias.strip():
                        names[norm(alias)] = code
    return names


def load_gazetteer(path):
    """Read GeoNames tab-separated cities1000.txt into city/country indexes."""
    by_city_country = defaultdict(list)
    by_ascii_country = defaultdict(list)
    by_city = defaultdict(list)

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 19:
                continue
            # GeoNames columns: 1=name, 2=ascii name, 4=lat, 5=lon,
            # 8=country code (all zero-based indexes below).
            name, ascii_name = cols[1], cols[2]
            try:
                lat, lon = float(cols[4]), float(cols[5])
            except ValueError:
                continue
            cc = cols[8].upper()
            population = int(cols[14] or 0)
            item = {"name": name, "ascii": ascii_name, "lat": lat,
                    "lon": lon, "cc": cc, "population": population}
            for city_name in {norm(name), norm(ascii_name)}:
                if city_name:
                    by_city_country[(city_name, cc)].append(item)
                    by_city[city_name].append(item)
            if norm(ascii_name):
                by_ascii_country[(norm(ascii_name), cc)].append(item)

    # Prefer the most populous settlement when a name is not unique.
    for index in (by_city_country, by_ascii_country, by_city):
        for key in index:
            index[key].sort(key=lambda x: x["population"], reverse=True)
    return by_city_country, by_ascii_country, by_city


def lookup_city(city, country, indexes, country_names=None):
    by_city_country, by_ascii_country, by_city = indexes
    city_key = norm(city)
    cc = country_code(country, country_names)
    if not city_key:
        return None, "empty city field"

    # Exact city + country match first.
    if cc:
        candidates = by_city_country.get((city_key, cc), [])
        if candidates:
            return candidates[0], None
        candidates = by_ascii_country.get((city_key, cc), [])
        if candidates:
            return candidates[0], None

    # If country is written as a full name, match it against GeoNames' country
    # code only after checking the built-in aliases. Do not silently select a
    # city in the wrong country when the city name is ambiguous.
    candidates = by_city.get(city_key, [])
    if not candidates:
        return None, f"city '{city}' not found in the gazetteer"
    if len({x["cc"] for x in candidates}) > 1:
        return None, (f"city '{city}' is ambiguous and country '{country}' could not be "
                      "matched; add its ISO-2 country code or extend COUNTRY_ALIASES")
    return candidates[0], None


def build_projector():
    """Project lon/lat into the existing SVG's coordinate system.

    The embedded map's graticule shows the central meridian at x=600 and
    the equator at y=310. The map artwork is already positioned within its
    1200 x 620 viewBox, so fitting a fresh projection to the whole canvas
    causes the dots to drift away from the land. Use the map's own scale and
    translation instead. These constants are calibrated from the graticule
    geometry in _includes/interactive-map.html.
    """
    import math

    # Calibrated against the embedded map's graticule paths.
    MAP_SCALE = 218.0
    MAP_CENTER_X = 600.0
    MAP_EQUATOR_Y = 310.0

    def natural_earth1(lon, lat):
        """D3 geoNaturalEarth1 equations; input degrees, output projected units."""
        lam = math.radians(lon)
        phi = max(-math.pi / 2, min(math.pi / 2, math.radians(lat)))
        p2 = phi * phi
        p4 = p2 * p2
        x = lam * (0.8707 - 0.131979 * p2
                   + p4 * (-0.013791 + p4 * (0.003971 - 0.001529 * p2)))
        y = phi * (1.007226 + p2 * (
            0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)
        ))
        return x, y

    def project(lat, lon):
        x, y = natural_earth1(lon, lat)
        return round(MAP_CENTER_X + MAP_SCALE * x, 2), round(MAP_EQUATOR_Y - MAP_SCALE * y, 2)

    return project


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_csv", help="CSV containing city and country columns")
    parser.add_argument("output_csv", help="output CSV for Jekyll _data/members.csv")
    parser.add_argument("--gazetteer", required=True, help="path to GeoNames cities1000.txt")
    parser.add_argument("--country-info", help="optional GeoNames countryInfo.txt (auto-detected beside the gazetteer)")
    parser.add_argument("--strict", action="store_true", help="fail if any city cannot be resolved")
    args = parser.parse_args()

    input_path, output_path, gazetteer_path = map(Path, (args.input_csv, args.output_csv, args.gazetteer))
    if not input_path.exists():
        sys.exit(f"Input CSV not found: {input_path}")
    if not gazetteer_path.exists():
        sys.exit(f"Gazetteer not found: {gazetteer_path}\nDownload cities1000.zip from https://download.geonames.org/export/dump/cities1000.zip")

    with input_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            sys.exit("Input CSV is empty or has no header row.")
        missing = [field for field in INPUT_REQUIRED if field not in reader.fieldnames]
        if missing:
            sys.exit("Missing required CSV column(s): " + ", ".join(missing) +
                     "\nExpected: " + ",".join(INPUT_REQUIRED))
        rows = list(reader)

    indexes = load_gazetteer(gazetteer_path)
    country_info_path = Path(args.country_info) if args.country_info else gazetteer_path.with_name("countryInfo.txt")
    country_names = load_country_names(country_info_path)
    project = build_projector()
    output_rows, errors = [], []

    for row_number, row in enumerate(rows, start=2):
        found, error = lookup_city(row.get("city", ""), row.get("country", ""), indexes, country_names)
        if error:
            errors.append(f"line {row_number}: {error} (country: {row.get('country', '')})")
            continue
        map_x, map_y = project(found["lat"], found["lon"])
        output_rows.append({
            "name": row.get("name", "").strip(),
            "institution": row.get("institution", "").strip(),
            "country": row.get("country", "").strip(),
            "latitude": f"{found['lat']:.5f}",
            "longitude": f"{found['lon']:.5f}",
            "map_x": f"{map_x:.2f}",
            "map_y": f"{map_y:.2f}",
            "research_areas": row.get("research_areas", "").strip(),
            "profile_url": row.get("profile_url", "").strip(),
        })

    if errors:
        print("Could not resolve these row(s):", file=sys.stderr)
        for error in errors:
            print("  - " + error, file=sys.stderr)
        if args.strict:
            sys.exit(f"Stopped: {len(errors)} unresolved row(s). No output written.")

    if not output_rows:
        sys.exit("No locations were resolved; no output written.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote {len(output_rows)} member(s) to {output_path}.")
    if errors:
        print(f"Skipped {len(errors)} unresolved row(s). Fix the city/country names and rerun.")
    print("Projection: D3 geoNaturalEarth1; confirm alignment against the embedded SVG before publishing.")


if __name__ == "__main__":
    main()
