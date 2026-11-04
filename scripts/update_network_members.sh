
#!/bin/bash

set -euo pipefail

# Load local environment variables
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# --------------------------------------------------
# MANTLE NETWORK – Member directory map update
# --------------------------------------------------

LIST_NAME="The MANTLE NETWORK Initiative - Member directory"
SNAPSHOT="data/private/laposta_member_directory.json"

echo "=========================================="
echo " MANTLE NETWORK – Member directory map update"
echo "=========================================="

# 1. Check API key
if [[ -z "${LAPOSTA_API_KEY:-}" ]]; then
    echo "ERROR: LAPOSTA_API_KEY is not set."
    exit 1
fi

# 2. Retrieve members from Laposta
echo ""
echo "[1/3] Retrieving members from Laposta..."

python scripts/geocode_subscribers.py \
    --laposta \
    --list-name "$LIST_NAME" \
    --member-state active \
    --snapshot "$SNAPSHOT" \
    --dry-run

# 3. Process snapshot and update website data
echo ""
echo "[2/3] Processing members and updating directory..."

python scripts/geocode_subscribers.py \
    --input "$SNAPSHOT" \
    --output _data/network_members.csv \
    --review reports/network_review.csv \
    --keywords reports/network_keywords.csv \
    --min-members 1 \
    --max-drop-fraction 0.5

# 4. Display summary
echo ""
echo "[3/3] Update completed."

echo "------------------------------------------"
echo "Members in directory: $(($(wc -l < _data/network_members.csv) - 1))"
echo "Updated: _data/network_members.csv"
echo "Review:  reports/network_review.csv"
echo "Keywords: reports/network_keywords.csv"
echo "Snapshot: $SNAPSHOT"
echo "------------------------------------------"

echo ""
echo "Run 'bundle exec jekyll serve' to preview."
