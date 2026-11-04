#!/bin/bash

set -euo pipefail

# Load local environment variables
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# --------------------------------------------------
# MANTLE NETWORK – Scientific committee map update
# --------------------------------------------------

LIST_NAME="The MANTLE NETWORK Initiative - Scientific committee"
SNAPSHOT="data/private/laposta_committee.json"

echo "=========================================="
echo " MANTLE NETWORK – Scientific committee map update"
echo "=========================================="

# 1. Check API key
if [[ -z "${LAPOSTA_API_KEY:-}" ]]; then
    echo "ERROR: LAPOSTA_API_KEY is not set."
    exit 1
fi

# 2. Retrieve data from Laposta and save snapshot
echo ""
echo "[1/3] Retrieving committee members from Laposta..."

python scripts/geocode_subscribers.py \
    --laposta \
    --list-name "$LIST_NAME" \
    --member-state active \
    --snapshot "$SNAPSHOT" \
    --dry-run

# 3. Process snapshot and update website data
echo ""
echo "[2/3] Processing members and updating map..."

python scripts/geocode_subscribers.py \
    --input "$SNAPSHOT" \
    --output _data/committee_members.csv \
    --review reports/committee_review.csv \
    --keywords reports/committee_keywords.csv

# 4. Display summary
echo ""
echo "[3/3] Update completed."

echo "------------------------------------------"
echo "Members in map: $(($(wc -l < _data/committee_members.csv) - 1))"
echo "Unresolved locations:"

grep -c "unresolved" reports/committee_review.csv || true

echo "------------------------------------------"
echo "Updated: _data/committee_members.csv"
echo "Review:  reports/committee_review.csv"
echo "Keywords: reports/committee_keywords.csv"
echo "Snapshot: $SNAPSHOT"
echo ""
echo "Run 'bundle exec jekyll serve' to preview."
