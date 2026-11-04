# The MANTLE NETWORK Initiative website

This repository contains the source code and content for [mantlenetwork.org](https://mantlenetwork.org), the website of **The MANTLE NETWORK Initiative**.

The site is built with **Jekyll**, **Liquid**, **Markdown**, **YAML** and **SCSS**, and is published through GitHub Pages. It is designed for shared maintenance: routine editorial updates should generally require only Markdown or YAML, while changes to presentation and behaviour belong in layouts, includes, stylesheets and JavaScript.

This README focuses on the website itself. The member-directory and newsletter automation are supporting features and are documented separately in [`_data/README.md`](./_data/README.md).

---

## 1. Getting started

### Requirements

- Git
- Ruby and Bundler
- Python 3 only if you need to run the supporting data scripts

Ruby dependencies are declared in `Gemfile` and locked in `Gemfile.lock`. Python dependencies are listed in `requirements.txt`.

### Run the website locally

```bash
git clone https://github.com/themantlenetwork/themantlenetwork.github.io.git
cd themantlenetwork.github.io
bundle install
bundle exec jekyll serve
```

Open the local address printed by Jekyll (normally `http://127.0.0.1:4000`). Jekyll rebuilds the site when source files change. Stop it with `Ctrl+C`.

To build without starting the local server:

```bash
bundle exec jekyll build
```

The generated website is written to `_site/`. This is build output: do not edit it or commit it.

### Optional Python environment

Python is not required to edit content or preview the website.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`.

---

## 2. How the website is assembled

Jekyll converts the repository's source files into a static website. Its main building blocks are:

1. **Markdown and HTML content** — the text and page-specific content.
2. **YAML front matter and data files** — page metadata, collection settings, navigation and structured content.
3. **Layouts** — reusable page templates.
4. **Includes** — reusable Liquid/HTML components inserted into layouts or pages.
5. **SCSS** — visual design, typography, responsive behaviour and component styling.
6. **JavaScript** — interactive features such as navigation, search and the image slider.
7. **Assets** — images, icons, documents, stylesheets and scripts.

A simplified rendering chain:

```text
Markdown / HTML page
        │
        ▼
Page layout (_layouts/)
        │
        ├── Shared components (_includes/)
        │      ├── head, navigation, masthead, footer
        │      ├── page intro, hero slider
        │      └── news, highlight, agenda, maps
        │
        ▼
Default layout (_layouts/default.html)
        │
        ├── SCSS → assets/stylesheets/main.css
        └── JavaScript → assets/javascripts/
        │
        ▼
Generated page in _site/
```

The `default` layout provides the site-wide frame. Other layouts build on it and add page-specific structures.

---

## 3. Repository structure

```text
.
├── _config.yml
├── _data/
│   ├── theme.yml
│   ├── committee_members.csv
│   ├── network_members.csv
│   └── README.md
├── _events/
├── _highlights/
├── _includes/
│   ├── icon/
│   └── search/
├── _layouts/
├── _pages/
├── _posts/
├── _sass/
│   └── theme/
├── assets/
│   ├── images/
│   ├── javascripts/
│   └── stylesheets/
├── forms/
├── resources/
├── scripts/
├── .github/
│   └── workflows/
├── index.md
├── Gemfile
├── Gemfile.lock
└── requirements.txt
```

| Location | Purpose | Typical changes |
|---|---|---|
| `index.md` | Homepage content and slider configuration | Homepage text, slides, images and links |
| `_pages/` | Main website pages | About, research, meetings, webinars, agenda, committee, contact |
| `_posts/` | Dated news posts | News and announcements |
| `_events/` | Structured event records | Meeting dates, venue, description, registration link |
| `_highlights/` | Short prominent announcements | Homepage or page highlight |
| `_layouts/` | Page templates | Change the structure or composition of page types |
| `_includes/` | Reusable Liquid/HTML components | Navigation, footer, slider, agenda, news and repeated blocks |
| `_data/` | Structured data and theme configuration | Navigation, member data and other site data |
| `_sass/` | Theme SCSS partials | Global design and component styling |
| `assets/stylesheets/` | Main SCSS entry point | Site-specific style overrides |
| `assets/javascripts/` | Browser-side scripts | Slider, navigation and interactions |
| `assets/images/` | Website images | Banners, photographs, logos and illustrations |
| `forms/` | Standalone HTML form and confirmation pages | Subscription and committee forms |
| `resources/` | Downloadable resources | Reports, abstracts and other documents |
| `scripts/` | Python and shell automation | Data preparation and update scripts |
| `.github/workflows/` | Scheduled GitHub Actions | Automation schedules and workflows |

The `_sass/theme/` directory contains the SCSS foundation and component partials. It is not a place for ordinary page content.

---

## 4. Pages, Markdown and YAML front matter

Most content pages live in `_pages/` and are written in Markdown (`.md`). A page normally starts with YAML front matter:

```yaml
---
layout: page
title: About
permalink: /about/
image: /assets/images/trinity_hero.jpg
---
```

The front matter tells Jekyll how to publish the page and which layout and optional components to use.

Common fields used by the current layouts and includes:

| Field | Meaning |
|---|---|
| `layout` | Selects a template from `_layouts/` |
| `title` | Page title |
| `permalink` | Explicit public URL |
| `image` | Optional introductory image |
| `sub_title` | Optional subtitle in the page intro |
| `introduction` | Optional introductory text in the page intro |
| `caption` | Optional image caption |
| `slides` | Slider content for layouts that include the hero slider |
| `slider_ratio` | Display ratio passed to the hero slider |

Not every field is used by every layout. Check the selected layout and its includes before adding new front-matter fields.

### Markdown content

```markdown
## Section heading

A paragraph with **bold text**, *emphasis* and [a link](https://example.org).

- First point
- Second point

![Descriptive alternative text](/assets/images/example.jpg)
```

Raw HTML is also used where a page needs a component that is not convenient to express in Markdown. Existing pages use HTML for styled buttons, grouped links and Liquid include statements.

### Liquid in content

Jekyll processes Liquid tags in Markdown pages. A page can insert a shared component:

```liquid
{% include highlight.html %}
```

Prefer an include when a block is reused or generated from a collection. Keep page-specific prose in the Markdown file.

### Adding a page

1. Create a Markdown file in `_pages/`.
2. Add valid front matter with a `layout`, `title` and `permalink`.
3. Write the page body in Markdown.
4. Add the page to the navigation configuration if it belongs in the main menu.
5. Preview it locally.
6. Check links, images and mobile layout before publishing.

Use consistent public URLs, preferably with a trailing slash, e.g. `/about/`.

---

## 5. Layouts: page templates

Layouts live in `_layouts/`. They define the structure surrounding page content and decide which reusable components are displayed.

### `default.html`

The site-wide wrapper. It includes:

- `head.html` for metadata, stylesheet and optional fonts;
- `lists.html`;
- skip links and sidebar controls;
- `navigation.html` and `contact-list.html`;
- `masthead.html`;
- the page body (`{{ content }}`);
- the search form;
- `footer.html` and `scripts.html`.

All other page layouts ultimately use this default layout.

### `page.html`

The standard content-page layout. It includes `page-intro.html`, then places the page body inside the main content area. It is used for ordinary pages such as About, Agenda and Scientific Committee.

### `page-slider.html`

Adds `hero-slider.html` before the normal page content. Slider content is configured through the page's `slides` front matter.

### `home-slider-news-box.html`

Used by `index.md`. It displays the hero slider, homepage text and `news-box.html`.

### `page-agenda-box.html`

Displays the standard page introduction and page body, followed by `agenda-box.html`.

### Choosing a layout

| Page type | Layout |
|---|---|
| Standard text/information page | `page` |
| Page with a large image slider | `page-slider` |
| Homepage with slider and latest news | `home-slider-news-box` |
| Page with an agenda callout below its content | `page-agenda-box` |

When introducing a page type, first consider whether an existing layout plus one or more includes is sufficient. Create a new layout only when the composition is genuinely different.

---

## 6. Includes: reusable components

Includes live in `_includes/`. They are HTML/Liquid files inserted into layouts or pages with `{% include filename.html %}`.

Main components currently present:

| Include | Role |
|---|---|
| `head.html` | Metadata, SEO tag, favicon, main CSS and optional fonts |
| `masthead.html` | Site logo and title |
| `navigation.html` | Main navigation menu |
| `contact-list.html` | Social links and partner links in the sidebar |
| `footer.html` | Site footer and credits link |
| `page-intro.html` | Page title, image, caption, subtitle, introduction and optional action buttons |
| `hero-slider.html` | Image slider with captions, links, buttons and credits |
| `news-box.html` | Latest news and promoted upcoming events |
| `highlight.html` | Most recent item in `_highlights/` |
| `agenda.html` | Upcoming events from `_events/` |
| `agenda-box.html` | Agenda callout below selected pages |
| `agenda-link.html` | Compact agenda heading and link |
| `committee-map.html` | Interactive scientific committee map and member presentation |
| `network-map.html` | Network/member map component |
| `coming-soon.html` | Reusable coming-soon notice |
| `work-in-progress.html` | Reusable work-in-progress notice |
| `bottom-focus.html` | Focus callout component |
| `google-analytics.html` | Analytics script, included in production |
| `scripts.html` | Main JavaScript, slider and search scripts |
| `search-form.html` | Search interface |
| `entry.html` | Reusable post/listing entry |
| `lists.html` | Shared list-related markup |
| `skip-links.html` | Keyboard accessibility navigation |

The `icon/` and `search/` subdirectories contain icon and search-provider components.

### Passing information to an include

Liquid includes can receive parameters. For example, a slider layout calls:

```liquid
{% include hero-slider.html slides=page.slides %}
```

Inside `hero-slider.html`, the value is available as `include.slides`.

Pass values into reusable includes rather than duplicating their HTML across several pages.

### Editing an include safely

1. Search for `{% include filename.html %}` to find every use.
2. Check which variables it expects (`page.*`, `site.*`, `include.*` or collection data).
3. Preserve optional-field checks so missing values do not create empty links or broken markup.
4. Preview every page that uses the component.

Changes to `masthead.html`, `navigation.html`, `head.html` or `footer.html` can affect the whole website.

---

## 7. Collections: events, highlights and news

Jekyll collections store related content as individual files with structured front matter. They let the site generate lists and callouts without manually maintaining the same information in several places.

### Events: `_events/`

Each event is a Markdown file with YAML metadata. The filename convention starts with the event date, followed by a short identifier.

```yaml
---
title: "GLOM 2027 — Oceanic Lithosphere: From Ophiolite to Ridge and Back"
event_date: 2027-02-02
end_date: 2027-02-03
location: "Rome, Italy"
link: "https://example.org/meeting"
event_id: glom-2027
banner: glom2027-banner.png
news: false
excerpt: >
  A short description for news and listing contexts.
---

The full event description goes here, in Markdown.
```

Fields used by the current agenda/news components:

- `title`: event name;
- `event_date`: first day;
- `end_date`: optional final day;
- `location`: venue or location;
- `link`: external information or registration page;
- `event_id`: stable HTML anchor;
- `banner`: optional image filename in `assets/images/events/`;
- `news`: whether the event may be promoted in the latest-news box;
- `excerpt`: short summary for news contexts.

The agenda sorts events by `event_date` and displays those whose end date (or event date if there is no end date) is not in the past. The news component can promote upcoming events marked `news: true`.

Use a unique `event_id`, valid `YYYY-MM-DD` dates, and preview both `/agenda/` and the homepage after adding an event.

### Highlights: `_highlights/`

Highlights are short announcements used by `highlight.html`. The include selects the most recent item by `date`.

```yaml
---
title: "Our first webinar series is coming in 2027!"
date: 2026-10-15
link: "/subscribe/"
link_text: "Subscribe to the newsletter →"
excerpt: >
  Stay tuned for the programme and upcoming announcements.
---
```

Fields:

- `title`: announcement heading;
- `date`: date used to select the latest highlight;
- `excerpt`: short text;
- `link`: optional destination;
- `link_text`: optional button label, used when `link` is provided.

If `link` is omitted, the highlight is displayed without a button. Add a new dated file to replace the current highlight; older entries remain in the collection.

### News: `_posts/`

Jekyll posts are dated Markdown files, conventionally named `YYYY-MM-DD-short-title.md`. They can be used for dated announcements and news entries.

The latest-news component combines posts with upcoming events marked `news: true`, then sorts the combined items by date.

---

## 8. Navigation and site configuration

### `_config.yml`

The main Jekyll configuration contains:

- site title, language, description and canonical URL;
- author and social metadata;
- logo and social-media links;
- search and Google Analytics settings;
- form URLs;
- collection definitions;
- Jekyll plugins.

Change it carefully: YAML indentation is significant, and invalid configuration can prevent the site from building.

### `_data/theme.yml`

This file contains theme-level configuration. In particular, `navigation_pages` defines the intended order of pages in the main navigation:

```yaml
navigation_pages:
  - _pages/about.md
  - _pages/research.md
  - _pages/meetings.md
  - _pages/webinars.md
  - _pages/committee.md
  - _pages/agenda.md
  - _pages/contact.md
```

The navigation include uses these paths to look up pages and render their titles and URLs. When adding, removing or renaming a navigation page, update this list and verify the menu locally.

The same file defines optional Google Fonts. Remove the `google_fonts` section to use system fonts.

### YAML editing tips

- Use spaces, never tabs.
- Keep indentation consistent (normally two spaces).
- Quote strings containing punctuation or values that could be interpreted as YAML types.
- Use `|` or `>` for multi-line text.
- Rebuild locally after changing configuration or front matter.

---

## 9. Styling: SCSS and CSS

The site uses SCSS, which Jekyll compiles into CSS.

### `assets/stylesheets/main.scss`

This is the main stylesheet entry point. It imports the theme and then defines site-specific design tokens and overrides.

The current file includes:

- CSS custom properties for spacing and text/link colours;
- layout width and padding adjustments;
- typography and vertical rhythm;
- link styling and keyboard focus appearance;
- introductory image sizing and cropping;
- button-description spacing;
- general wrapper layout.

The browser loads the compiled `/assets/stylesheets/main.css`. Edit the `.scss` source, not generated CSS.

### `_sass/theme.scss`

This file imports the theme's SCSS modules:

- functions, variables and mixins;
- responsive breakpoint and grid utilities;
- reset, base, layout and table styles;
- syntax highlighting, responsive embeds and print styles;
- slider, global layout, sidebar, navigation and search;
- utilities, footer, entries, buttons, icons and page-intro styles.

Supporting partials are stored in `_sass/theme/`.

### Where should a style change go?

- **Site-wide typography, spacing, colours or layout overrides:** `assets/stylesheets/main.scss`.
- **A theme/component-level style:** the relevant partial in `_sass/theme/`, or a clearly labelled override in `main.scss`.
- **A one-off content variation:** add a semantic class to the markup and style that class.

Avoid editing compiled files in `_site/`. Keep custom rules grouped under comments and reuse existing CSS custom properties where practical.

### Existing component classes

Examples include:

- `.highlight-box`, `.hero-box` and `.focus-box` for announcement/callout blocks;
- `.intro-image`, `.intro-text` and `.intro-actions` for page introductions;
- `.button-description` for a button with supporting text;
- `.agenda-event` and related classes for event entries;
- `.btn` and page-specific classes such as `.btn-meetings`, `.btn-webinars` and `.btn-agenda`.

Use descriptive class names and avoid broad selectors that could unintentionally affect unrelated pages.

---

## 10. JavaScript and interactive features

Browser-side JavaScript lives in `assets/javascripts/`.

| File | Purpose |
|---|---|
| `main.js` | Main theme interactions, including navigation/sidebar and search behaviour |
| `slider.js` | Hero-slider controls |
| `lunr/` | Local search library and language support files |

The `scripts.html` include loads the main JavaScript and slider script, then loads the selected search-provider scripts when search is enabled.

The current search setup uses the theme's Lunr integration by default unless `search_provider` is set to another supported provider such as Algolia.

When changing JavaScript:

- keep the site usable on mobile and desktop;
- check keyboard interaction and focus behaviour;
- avoid unnecessary dependencies;
- test pages with and without the relevant component;
- check the browser console for errors.

The committee map is a more self-contained interactive component and includes substantial HTML, CSS and JavaScript in its include. Test its filters, map markers, member details and responsive display after changing it.

---

## 11. Images, icons and downloadable resources

### Images

Images are stored primarily in `assets/images/`. Pages refer to them using paths such as:

```yaml
image: /assets/images/trinity_hero.jpg
```

Use descriptive filenames and compress large images appropriately for web use. Large photographs increase page load time and repository size.

Slider entries can use fields such as `image`, `alt`, `title`, `text`, `caption_url`, `button_text`, `button_url` and `credit`. Provide meaningful alternative text where appropriate and preserve required image credits.

### Icons

Reusable icon files and wrappers are stored in `_includes/icon/`. Prefer an existing icon include rather than duplicating an SVG in several pages.

### Documents

Downloadable files such as PDFs are stored in `resources/` or another clearly named asset directory. Link to them using their site-relative path.

---

## 12. Forms, data and automation

These are supporting services rather than the core content architecture:

- `forms/` contains subscription and scientific committee form pages and confirmation pages.
- `scripts/` contains Python and shell scripts for member and newsletter data.
- `.github/workflows/` contains scheduled GitHub Actions for data-update processes.
- `_data/` contains structured data used by Jekyll, including public committee/network datasets and `theme.yml`.

See [`_data/README.md`](./_data/README.md) for the detailed data workflows, inputs/outputs and credentials. Python is not needed for normal content editing or local website previews.

### Secrets

Never commit API keys, passwords, private subscriber exports or credentials. The Laposta API key is supplied locally through an ignored `.env` file and in GitHub Actions through repository secrets. Do not place credentials in Markdown, YAML, HTML, JavaScript or commit history.

---

## 13. Publishing and collaborative maintenance

The website is maintained from the repository's publishing branch. Changes merged or pushed to that branch are picked up by the configured GitHub Pages publishing process.

Recommended contribution workflow:

1. Create a branch for a change rather than editing the publishing branch directly.
2. Make a focused change: content, event metadata, styles or a component.
3. Run `bundle exec jekyll serve`.
4. Review the affected page and other pages that share the modified layout/include.
5. Check desktop and mobile widths, links, images and browser-console errors.
6. Commit with a descriptive message.
7. Open a pull request for review.
8. Merge once the change has been checked.

For routine editorial updates, a contributor can usually work only in Markdown or YAML. Changes to layouts, includes, SCSS, JavaScript, configuration and workflows should be reviewed by someone familiar with the site structure.

### Contribution levels

| Contribution | Files | Skills |
|---|---|---|
| Correct text or links | `_pages/*.md` | Basic Markdown |
| Add a meeting | `_events/*.md` | Markdown + YAML |
| Publish an announcement | `_highlights/*` or `_posts/*` | Markdown + YAML |
| Change homepage slides | `index.md` | Markdown + YAML |
| Add/reorder menu items | `_data/theme.yml` | YAML |
| Add a page type | `_layouts/`, `_includes/` | Liquid + HTML |
| Change appearance | `assets/stylesheets/main.scss`, `_sass/` | SCSS/CSS |
| Change interactive behaviour | `assets/javascripts/`, relevant include | JavaScript |
| Change site-wide settings | `_config.yml` | YAML/Jekyll |
| Change automated data updates | `scripts/`, `.github/workflows/` | Python, shell, GitHub Actions |

### Keeping the website maintainable

- Keep content separate from presentation.
- Reuse existing layouts and includes.
- Use collections for repeated structured content such as events and highlights.
- Keep YAML fields consistent across collection entries.
- Document non-obvious Liquid logic and JavaScript behaviour.
- Make small, reviewable pull requests.
- Never edit generated output.
- Keep secrets and private data out of the public repository.
- Periodically review dependencies and GitHub Actions.

The aim is for routine editorial work to be possible without understanding the whole codebase, while keeping the design and functionality understandable to future maintainers.

---

## 14. Troubleshooting

### Jekyll does not start

```bash
bundle install
bundle exec jekyll serve
```

Check that the installed Ruby version is compatible with the dependencies in `Gemfile.lock`.

### A page does not appear

Check that the file is in `_pages/`, its front matter is valid YAML, it has a valid layout, its permalink is unique, and the `pages` collection is configured in `_config.yml`.

### A page is missing from the navigation

Check its path in `_data/theme.yml` and confirm the navigation include can resolve it. Rebuild the site afterwards.

### A style change has no effect

Check that you edited `assets/stylesheets/main.scss`, that the selector matches the page markup, and that Jekyll recompiled the stylesheet. Do not edit `_site/assets/stylesheets/main.css`.

### An include breaks several pages

Search for the include filename to find every use. Check its Liquid syntax and whether optional variables are handled safely. Test every affected page.

### A collection item is not displayed

Check its front matter, required date fields and collection name. For events, verify `event_date`, optional `end_date` and `event_id`. For highlights, verify `date`.

---

## 15. Further documentation

- [`_data/README.md`](./_data/README.md) — member directory, committee and newsletter data workflows.
- [`Gemfile`](./Gemfile) and [`Gemfile.lock`](./Gemfile.lock) — Ruby/Jekyll dependencies.
- [`requirements.txt`](./requirements.txt) — Python dependencies for supporting scripts.
- [Jekyll documentation](https://jekyllrb.com/docs/) — pages, layouts, includes, collections and configuration.
- [Liquid documentation](https://shopify.github.io/liquid/) — template language used in layouts and includes.
- [Sass documentation](https://sass-lang.com/documentation/) — SCSS syntax and compilation.
- [GitHub Pages documentation](https://docs.github.com/en/pages) — publishing and deployment.

---

*This README describes the repository's current structure and implementation. Update it alongside future changes to layouts, includes, collections or the build process.*
