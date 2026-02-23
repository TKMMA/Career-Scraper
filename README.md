# Career Scraper / Embed Tables

This repository builds `jobs.json` and renders two DataTables in `index.html`:

- **Civil Service Listings**
- **Contract Positions through RCUH**

## How data gets into the tables

1. GitHub Action (`.github/workflows/update_jobs.yml`) runs `python scraper.py` daily.
2. `scraper.py` writes `jobs.json` into the repo.
3. `index.html` fetches `jobs.json` and populates both DataTables.

If you host `index.html` and `jobs.json` together (for example GitHub Pages), the tables will auto-populate.

## Why tables might be empty

- The source site blocks automation or data center IP ranges.
- The source site changed HTML selectors.
- Temporary network failures.

The scraper now writes errors into `jobs.json.errors` and marks fallback usage in `jobs.json.fallbacks`.

## Indeed workaround

If direct scraping returns no rows, the scraper tries Indeed RSS fallback queries:

- Civil Service fallback query: `Hawaii Land Natural Resources civil service`
- RCUH fallback query: `Research Corporation University of Hawaii RCUH`

Rows coming from this fallback are tagged with `source: "indeed"` and displayed with an **Indeed** badge in the table.

## Embed options

### Option A: iframe (simplest)
Host this project on GitHub Pages and embed:

```html
<iframe
  src="https://<org>.github.io/<repo>/index.html"
  style="width:100%; height:1200px; border:0;"
  loading="lazy"
></iframe>
```

### Option B: JSON-only + your own frontend
Use only `jobs.json` from GitHub raw/pages and render with your site framework.

---

If you need a stronger production setup, next step is a small serverless function (Cloudflare Worker / AWS Lambda) that fetches upstream data and returns normalized JSON with cache + retries.
