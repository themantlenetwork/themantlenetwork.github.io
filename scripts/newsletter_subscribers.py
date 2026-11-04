#!/usr/bin/env python3
"""Retrieve active MANTLE NETWORK newsletter subscribers from Laposta.

Writes:
- _data/private/newsletter/laposta_snapshot.json: complete member records and retrieval metadata
- _data/private/newsletter/subscribers.csv: flattened CSV of the returned member fields

No geocoding, map generation, keyword processing, or public website output.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

API_BASE = "https://api.laposta.org/v2"
DEFAULT_LIST_NAME = "The MANTLE NETWORK Initiative - Newsletter"
DEFAULT_JSON = "_data/private/newsletter/laposta_snapshot.json"
DEFAULT_CSV = "_data/private/newsletter/subscribers.csv"


def laposta_get(session, endpoint, params=None):
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    for attempt in range(5):
        try:
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt == 4:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else min(2 ** attempt, 30))
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


def fetch_members(api_key, list_name, member_state):
    session = requests.Session()
    session.auth = HTTPBasicAuth(api_key, "")
    session.headers.update({"Accept": "application/json"})

    lists_payload = laposta_get(session, "list")
    matches = []
    for entry in lists_payload.get("data", []):
        obj = entry.get("list", entry) if isinstance(entry, dict) else {}
        if obj.get("name") == list_name:
            matches.append(obj)

    if len(matches) != 1:
        available = [
            (entry.get("list", entry)).get("name", "")
            for entry in lists_payload.get("data", [])
            if isinstance(entry, dict)
        ]
        raise RuntimeError(
            f"Expected exactly one Laposta list named {list_name!r}; "
            f"found {len(matches)}. Available lists: {available}"
        )

    selected_list = matches[0]
    list_id = selected_list.get("list_id")
    if not list_id:
        raise RuntimeError("Laposta list response did not include list_id.")

    members = []
    cursor = None
    seen_cursors = set()

    while True:
        params = {"list_id": list_id, "limit": 1000}
        if member_state != "all":
            params["state"] = member_state
        if cursor:
            if cursor in seen_cursors:
                raise RuntimeError("Laposta returned a repeated pagination cursor.")
            seen_cursors.add(cursor)
            params["cursor"] = cursor

        payload = laposta_get(session, "member", params)
        for entry in payload.get("data", []):
            member = entry.get("member", entry) if isinstance(entry, dict) else None
            if isinstance(member, dict):
                members.append(member)

        pagination = payload.get("pagination") or {}
        if not pagination.get("has_more"):
            break
        cursor = pagination.get("next_cursor")
        if not cursor:
            raise RuntimeError("Laposta pagination indicates more records but has no next_cursor.")

    metadata = {
        "source": "Laposta API",
        "list_name": selected_list.get("name", list_name),
        "list_id": list_id,
        "member_state_filter": member_state,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(members),
    }
    return members, metadata


def flatten_member(member):
    """Flatten custom_fields into CSV columns while retaining other member fields."""
    row = {}
    for key, value in member.items():
        if key == "custom_fields":
            if isinstance(value, dict):
                for custom_key, custom_value in value.items():
                    row[f"custom_{custom_key}"] = csv_value(custom_value)
            else:
                row["custom_fields"] = csv_value(value)
        else:
            row[key] = csv_value(value)
    return row


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def write_outputs(json_path, csv_path, members, metadata):
    json_target = Path(json_path)
    csv_target = Path(csv_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    csv_target.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {"metadata": metadata, "members": members}
    json_target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rows = [flatten_member(member) for member in members]
    # Union of keys preserves fields even when they are absent from some records.
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    if not fieldnames:
        fieldnames = ["email"]

    with csv_target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-name", default=DEFAULT_LIST_NAME)
    parser.add_argument(
        "--member-state",
        choices=("active", "unsubscribed", "bounced", "all"),
        default="active",
    )
    parser.add_argument("--snapshot", default=DEFAULT_JSON)
    parser.add_argument("--output", default=DEFAULT_CSV)
    parser.add_argument("--min-subscribers", type=int, default=1)
    args = parser.parse_args()

    api_key = os.environ.get("LAPOSTA_API_KEY", "").strip()
    if not api_key:
        sys.exit("ERROR: LAPOSTA_API_KEY environment variable is not set.")

    try:
        members, metadata = fetch_members(api_key, args.list_name, args.member_state)
    except Exception as exc:
        sys.exit(f"Laposta error: {exc}")

    if len(members) < args.min_subscribers:
        sys.exit(
            f"Safety check failed: retrieved {len(members)} subscribers; "
            f"minimum is {args.min_subscribers}. No output files written."
        )

    write_outputs(args.snapshot, args.output, members, metadata)

    print("Newsletter subscriber update completed.")
    print("----------------------------------------")
    print(f"List:        {metadata['list_name']}")
    print(f"State:       {args.member_state}")
    print(f"Subscribers: {len(members)}")
    print(f"JSON:        {args.snapshot}")
    print(f"CSV:         {args.output}")


if __name__ == "__main__":
    main()
