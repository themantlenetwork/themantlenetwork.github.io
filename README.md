# MANTLE NETWORK data directory

This directory contains the public data files used by the MANTLE NETWORK
website, reference data required by the member-processing scripts, and a
private working area for data retrieved from Laposta.

## Directory structure

``` text
_data/
├── committee_members.csv
├── network_members.csv
├── reference/
│   ├── cities1000.txt
│   └── countryInfo.txt
└── private/                       # ignored by Git
    ├── committee/
    │   ├── laposta_snapshot.json
    │   ├── committee_review.csv
    │   └── committee_keywords.csv
    ├── network/
    │   ├── laposta_snapshot.json
    │   ├── network_review.csv
    │   └── network_keywords.csv
    └── newsletter/
        ├── laposta_snapshot.json
        └── subscribers.csv
```

The private directories and their contents are not committed to the
repository. The public CSV files are the data products intended for use
by the website.

## Data sources and outputs

  -------------------------------------------------------------------------------
  Dataset           Source            Public output             Private outputs
  ----------------- ----------------- ------------------------- -----------------
  Scientific        Laposta committee `committee_members.csv`   Snapshot, review
  committee         list                                        CSV and keyword
                                                                CSV

  Network directory Laposta           `network_members.csv`     Snapshot, review
                    network/member                              CSV and keyword
                    list                                        CSV

  Newsletter        Laposta           None                      Snapshot and
                    newsletter list                             subscribers CSV
  -------------------------------------------------------------------------------

Newsletter subscriber data is not published on the website. The
newsletter workflow only creates and uploads a private artifact; it does
not commit or push generated files to the repository.

## Processing scripts

The scripts are located in `scripts/` at the repository root.

-   `geocode_members.py` is the shared processing script for committee
    and network datasets. It processes the relevant Laposta data, uses
    the GeoNames reference files for geocoding, and generates the public
    CSV and private review outputs.
-   `update_committee_members.sh` runs the committee update.
-   `update_network_members.sh` runs the network directory update.
-   `newsletter_subscribers.py` retrieves newsletter subscribers from
    Laposta and generates the private newsletter snapshot and CSV.
-   `update_newsletter_subscribers.sh` runs the newsletter update.

The committee and network launchers use the same processing logic but
write to separate public and private destinations.

## GeoNames reference data

The files in `reference/` support the geocoding performed by
`geocode_members.py`:

-   `cities1000.txt`
-   `countryInfo.txt`

The committee workflow downloads these reference files when it runs. The
network workflow uses the reference files already present in
`_data/reference/`.

## GitHub Actions workflows

Three workflows automate the updates. Each can be run manually and is
also scheduled to run weekly.

  ---------------------------------------------------------------------------------------------------------------------------
  Workflow file                               Purpose           Repository changes        Artifact
  ------------------------------------------- ----------------- ------------------------- -----------------------------------
  `.github/workflows/update-committee.yml`    Refresh committee Commits and pushes        `committee-private-<run number>`
                                              data              `committee_members.csv`   
                                                                only when it changes      

  `.github/workflows/update-directory.yml`    Refresh network   Commits and pushes        `network-private-<run number>`
                                              directory data    `network_members.csv`     
                                                                only when it changes      

  `.github/workflows/update-newsletter.yml`   Refresh           No commit or push;        `newsletter-private-<run number>`
                                              newsletter        repository permission is  
                                              subscriber data   read-only                 
  ---------------------------------------------------------------------------------------------------------------------------

### Committee workflow

1.  Checks out the repository and prepares the Python environment.
2.  Downloads the GeoNames reference files into `_data/reference/`.
3.  Runs `scripts/update_committee_members.sh`, using the
    `LAPOSTA_API_KEY` GitHub Actions secret.
4.  Generates `_data/committee_members.csv` and the private committee
    files.
5.  Commits and pushes the public CSV only if it has changed.
6.  Uploads `_data/private/committee/` as a downloadable GitHub Actions
    artifact.

### Network directory workflow

1.  Checks out the repository and prepares the Python environment.
2.  Uses the GeoNames files already stored in `_data/reference/`.
3.  Runs `scripts/update_network_members.sh`, using the
    `LAPOSTA_API_KEY` GitHub Actions secret.
4.  Generates `_data/network_members.csv` and the private network files.
5.  Commits and pushes the public CSV only if it has changed.
6.  Uploads `_data/private/network/` as a downloadable GitHub Actions
    artifact.

### Newsletter workflow

1.  Checks out the repository and prepares the Python environment.
2.  Runs `scripts/update_newsletter_subscribers.sh`, using the
    `LAPOSTA_API_KEY` GitHub Actions secret.
3.  Generates `_data/private/newsletter/laposta_snapshot.json` and
    `_data/private/newsletter/subscribers.csv`.
4.  Uploads `_data/private/newsletter/` as a downloadable GitHub Actions
    artifact.

The newsletter workflow does **not** commit or push anything. It has
read-only repository permissions. Its output is retained only as a
GitHub Actions artifact, subject to the configured artifact retention
period.

## Private files and Git

The repository `.gitignore` excludes the entire private data directory:

``` gitignore
_data/private/
```

This keeps raw snapshots, review files and newsletter subscriber
information out of Git history and out of the public website repository.

The private files are made available through GitHub Actions artifacts
for a limited period. The current workflows configure artifact retention
for 14 days.

### Artifact packaging

The workflows upload the relevant private directory directly with
`actions/upload-artifact@v4`.

Do not manually ZIP the private directory before uploading it. GitHub
Actions automatically packages an uploaded directory as a downloadable
ZIP archive. Manually creating a ZIP first would produce an archive
nested inside the GitHub artifact archive.

## Configuration and credentials

-   Local runs use `LAPOSTA_API_KEY` from the repository-root `.env`
    file.
-   GitHub Actions use the repository secret named `LAPOSTA_API_KEY`.
-   The API key must never be committed to Git or included in generated
    CSV, JSON or log output.

## Running updates locally

From the repository root, run the relevant launcher:

``` bash
bash scripts/update_committee_members.sh
bash scripts/update_network_members.sh
bash scripts/update_newsletter_subscribers.sh
```

Make sure the required Python environment and dependencies are installed
and that `.env` contains a valid `LAPOSTA_API_KEY`. The committee and
network scripts also require the GeoNames reference data in
`_data/reference/`; the committee workflow downloads these files
automatically.

## Current scope and future development

These scripts and workflows form the current CSV-based data-processing
pipeline. They keep the public website datasets separate from private
snapshots and administrative outputs.

A central database and a more comprehensive data-management layer may be
developed separately in the future. They are not part of the current
workflows described here.
