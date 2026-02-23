# Career Scraper / Embed Tables

This repository builds `jobs.json` and renders two DataTables in `index.html`:

- **Civil Service Listings**
- **Contract Positions through RCUH**

## Data flow

1. GitHub Action runs `python scraper.py` daily.
2. `scraper.py` fetches the DLNR jobs page (`https://dlnr.hawaii.gov/jobs/`) using lightweight HTTP requests.
3. The script parses Civil Service and RCUH data and writes `jobs.json`.
4. `index.html` fetches `jobs.json` and populates both tables.

## Why this approach is reliable in GitHub Actions

- No Selenium
- No Chrome/Chromedriver
- No browser automation dependencies

Only `requests` + `beautifulsoup4` are required.

## Output contract

`jobs.json` always contains:

- `civil_service` (array)
- `rcuh` (array)
- `errors` (array)
- `generated_at_utc` (timestamp)

If scraping fails, the script still writes a valid file with error details so the front end can keep running.

## Embed options

### Option A: iframe

```html
<iframe
  src="https://<org>.github.io/<repo>/index.html"
  style="width:100%; height:1200px; border:0;"
  loading="lazy"
></iframe>
```

### Option B: Render your own UI from JSON

Consume `jobs.json` directly from your hosting layer and render with your existing site framework.
