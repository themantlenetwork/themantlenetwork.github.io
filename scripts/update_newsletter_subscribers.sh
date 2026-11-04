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

echo "=========================================="
echo " MANTLE NETWORK – Newsletter subscribers"
echo "=========================================="

if [[ -z "${LAPOSTA_API_KEY:-}" ]]; then
    echo "ERROR: LAPOSTA_API_KEY is not set."
    echo "Add it to .env in the repository root."
    exit 1
fi

python scripts/newsletter_subscribers.py \
    --list-name "The MANTLE NETWORK Initiative - Newsletter" \
    --member-state active \
    --snapshot "_data/private/newsletter/laposta_snapshot.json" \
    --output "_data/private/newsletter/subscribers.csv" \
    --min-subscribers 1

echo ""
echo "Newsletter update completed."
echo "Files saved under _data/private/newsletter/."
