#!/bin/bash

set -e

# Generate website data
cd "/Users/romaintilhac/Documents/Research/resources/GitHub/themantlenetwork/themantlenetwork.github.io/_data"

python3 geocode_subscribers.py \
    "subscribers.xlsx" \
    --sheet "Subscribers" \
    --gazetteer cities1000.txt \
    --country-info countryInfo.txt \
    --output members.csv \
    --review members_review.csv \
    --keywords keyword_inventory.csv

# Start Jekyll server
cd "/Users/romaintilhac/Documents/Research/resources/GitHub/themantlenetwork/themantlenetwork.github.io/"

bundle exec jekyll serve
