# MANTLE NETWORK committee-map automation

This bundle adds a unified pipeline for Laposta, JSON snapshots, CSV and Excel
inputs. It writes the existing Jekyll map schema to `_data/members.csv`.

## Repository layout

Copy these files/folders into the root of the existing Jekyll repository:

```text
.github/workflows/update-committee.yml
scripts/geocode_subscribers.py
requirements.txt
```

Create these directories locally:

```text
data/private/       # private snapshots; never commit
data/reference/     # GeoNames reference files
reports/            # local review reports
```

The workflow downloads GeoNames data into `data/reference/` on each run. It
does not commit those reference files or private member data.

## Local setup

From the repository root:

```bash
python -m pip install -r requirements.txt
mkdir -p scripts data/private data/reference reports
```

Download GeoNames reference data:

```bash
curl -L https://download.geonames.org/export/dump/cities1000.zip -o /tmp/cities1000.zip
unzip -o /tmp/cities1000.zip -d data/reference
curl -L https://download.geonames.org/export/dump/countryInfo.txt -o data/reference/countryInfo.txt
```

Set the Laposta API key in your shell. Do not paste it into source code or
commit it:

```bash
export LAPOSTA_API_KEY="YOUR_NEW_LAPOSTA_API_KEY"
```

Run a dry test first:

```bash
python scripts/geocode_subscribers.py --laposta --dry-run
```

Then generate the outputs:

```bash
python scripts/geocode_subscribers.py \
  --laposta \
  --snapshot data/private/laposta_committee.private.json
```

Outputs:
- `_data/members.csv`: public Jekyll map data.
- `reports/members_review.csv`: contains email addresses; keep private.
- `reports/keyword_inventory.csv`: review of canonical research topics.
- `data/private/laposta_committee.private.json`: optional private source snapshot.

## Input options

Direct API retrieval:

```bash
python scripts/geocode_subscribers.py --laposta
```

Saved JSON snapshot:

```bash
python scripts/geocode_subscribers.py --input data/private/laposta_committee.private.json
```

CSV or Excel:

```bash
python scripts/geocode_subscribers.py --input path/to/export.csv
python scripts/geocode_subscribers.py --input path/to/export.xlsx --sheet Subscribers
```

Keyword standardisation is enabled by default. To preserve the submitted
research-area text instead:

```bash
python scripts/geocode_subscribers.py --laposta --no-standardize-keywords
```

The `--dry-run` option processes and reports counts without writing output
files. The map output is guarded against a large unexpected reduction in rows;
review the error before overriding with `--max-drop-fraction 1.0`.

## GitHub Actions setup

1. Push the workflow and script to the repository's default branch.
2. In GitHub, open **Settings → Secrets and variables → Actions**.
3. Create a repository secret named `LAPOSTA_API_KEY` containing the newly
   generated Laposta API key.
4. Open **Actions → Update scientific committee map → Run workflow**.
5. Inspect the run logs and download the `committee-map-review-*` artifact.
6. Confirm the map CSV change and the rendered website.

The workflow runs every Monday at 06:15 UTC and can also be triggered manually.
GitHub Actions requires the repository's Actions permissions to allow workflow
execution and write access to repository contents. The workflow grants only
`contents: write` for committing `_data/members.csv`.

Review reports are uploaded as short-lived workflow artifacts (14 days), not
committed. They contain personal data such as email addresses, so restrict
repository access accordingly and delete artifacts when no longer needed.

## Important membership-state decision

The workflow currently requests Laposta `active` members only. A mailing-list
state is not necessarily equivalent to committee membership. Confirm that
this is the intended inclusion rule before enabling the scheduled workflow.
If committee membership should be independent of email-delivery subscription
status, maintain that membership status separately rather than treating
Laposta's `active` state as authoritative.

## Safety and operational notes

- Rotate any API key previously pasted into a chat or committed to a repository.
- Never commit `data/private/`, `.env`, snapshots, or review reports.
- The workflow only commits `_data/members.csv`.
- GeoNames is downloaded at runtime; check its terms/attribution requirements
  for the way the map is used.
- GitHub scheduled workflows can be delayed during periods of high load.
- The action does not publish a map if the pipeline fails its row-count guard.
- The first automated run should be manual and reviewed before relying on the
  weekly schedule.
