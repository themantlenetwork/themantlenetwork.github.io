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

# Push updated files to remote repository
cd "/Users/romaintilhac/Documents/Research/resources/GitHub/themantlenetwork/themantlenetwork.github.io/"

git add _data/members.csv _data/keyword_inventory.csv

git commit -m "Update scientific committee members and keywords"

git push origin main

echo "Website data successfully updated and pushed to remote."
