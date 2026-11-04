#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

LIST_NAME="The MANTLE NETWORK Initiative - Scientific committee"
SNAPSHOT="_data/private/committee/laposta_snapshot.json"
OUTPUT="_data/committee_members.csv"
REVIEW="_data/private/committee/committee_review.csv"
KEYWORDS="_data/private/committee/committee_keywords.csv"

echo "=========================================="
echo " MANTLE NETWORK – Scientific committee update"
echo "=========================================="

if [[ -z "${LAPOSTA_API_KEY:-}" ]]; then
    echo "ERROR: LAPOSTA_API_KEY is not set. Add it to .env in the repository root."
    exit 1
fi

echo ""
echo "[1/2] Retrieving committee members from Laposta..."
python scripts/geocode_members.py \
    --laposta \
    --list-name "$LIST_NAME" \
    --member-state active \
    --snapshot "$SNAPSHOT" \
    --dry-run

echo ""
echo "[2/2] Processing committee members and updating map data..."
python scripts/geocode_members.py \
    --input "$SNAPSHOT" \
    --gazetteer "_data/reference/cities1000.txt" \
    --country-info "_data/reference/countryInfo.txt" \
    --output "$OUTPUT" \
    --review "$REVIEW" \
    --keywords "$KEYWORDS" \
    --min-members 1 \
    --max-drop-fraction 0.5

echo ""
echo "Scientific committee update completed."
echo "Members:  $(($(wc -l < "$OUTPUT") - 1))"
echo "Public:   $OUTPUT"
echo "Review:   $REVIEW"
echo "Keywords: $KEYWORDS"
echo "Snapshot: $SNAPSHOT"
echo ""
echo "Run 'bundle exec jekyll serve' to preview."
