# The MANTLE NETWORK Initiative

Official website of **The MANTLE NETWORK Initiative**, an international collective of researchers, students and professionals working to advance our understanding of the Earth's mantle.

Website: [mantlenetwork.org](https://mantlenetwork.org)

## About this repository

This repository contains the Jekyll website and the scripts and workflows used to maintain selected community datasets.

The site is built with [Jekyll](https://jekyllrb.com/), using the Basically Basic theme and custom layouts, includes and styles. GitHub Pages publishes the site at [mantlenetwork.org](https://mantlenetwork.org).

## Repository structure

```text
.
├── _config.yml                 # Jekyll configuration
├── _data/                      # Website datasets, references and data README
├── _events/                    # Event collection
├── _highlights/                # Homepage highlights
├── _includes/                  # Reusable Liquid/HTML components
├── _layouts/                   # Page layouts
├── _pages/                     # Main website pages
├── _posts/                     # News and blog posts
├── _sass/                      # Sass stylesheets
├── assets/                     # Images, fonts and other static assets
├── forms/                      # Form pages
├── resources/                  # Downloadable resources
├── scripts/                    # Python data processing and shell launchers
├── .github/workflows/          # Scheduled and manual data workflows
├── Gemfile                     # Ruby/Jekyll dependencies
├── Gemfile.lock                # Locked Ruby dependencies
├── requirements.txt            # Python script dependencies
└── README.md
```

## Run the website locally

Requirements: Ruby, Bundler and the dependencies specified in `Gemfile`.

From the repository root:

```bash
bundle install
bundle exec jekyll serve
```

Open the local address printed by Jekyll (usually http://localhost:4000). Changes to pages and most site files are rebuilt automatically while the server is running.

## Data maintenance

The repository includes automated Laposta pipelines for:

- the scientific committee map;
- the member directory map;
- the newsletter subscriber export.

The first two pipelines generate public CSV files used by the website, alongside private review outputs. The newsletter pipeline creates a private export only; it does not publish subscriber data or commit generated files.

For the data structure, inputs and outputs, local commands, GeoNames reference data, credentials and workflow details, see [`_data/README.md`](_data/README.md).

### Python environment

The data scripts use Python 3.12 in GitHub Actions. Install their dependencies with:

```bash
python -m pip install -r requirements.txt
```

Local Laposta updates require a root-level `.env` file containing `LAPOSTA_API_KEY`. In GitHub Actions, this is configured as a repository secret with the same name. Never commit credentials or private subscriber/member exports.

## GitHub Actions

The workflows under `.github/workflows/` run weekly and can also be triggered manually from the Actions tab:

- `update-committee.yml`
- `update-directory.yml`
- `update-newsletter.yml`

The committee and directory workflows push changes to their respective public CSV only when the generated file differs. The newsletter workflow uploads its private results as a downloadable artifact and does not push to the repository.

## Dependencies

- **Website:** Ruby dependencies are defined in `Gemfile` and locked in `Gemfile.lock`.
- **Data scripts:** Python dependencies are defined in `requirements.txt`.

## Privacy

Public website datasets belong in `_data/`. Private Laposta snapshots, subscriber exports and review files belong under `_data/private/` and must remain excluded from Git. Keep API credentials in local environment files or GitHub Actions secrets, never in source code.
