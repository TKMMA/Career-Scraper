import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

DLNR_JOBS_URL = "https://dlnr.hawaii.gov/jobs/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT_SECONDS = 40


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text




def build_soup(html: str) -> Any:
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required at runtime. Install dependencies with: pip install -r requirements.txt")
    return BeautifulSoup(html, "html.parser")

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def extract_link_from_cell(cell: Any, base_url: str) -> str:
    anchor = cell.find("a", href=True) if cell else None
    if not anchor:
        return base_url
    return urljoin(base_url, anchor["href"])


def row_to_cells(row: Any) -> list[str]:
    return [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]


def parse_civil_service_table(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []

    civil_heading = soup.find(
        lambda tag: tag.name in {"h2", "h3", "h4"}
        and "civil service" in clean_text(tag.get_text()).lower()
    )

    candidate_tables: list[Any] = []
    if civil_heading:
        next_table = civil_heading.find_next("table")
        if next_table:
            candidate_tables.append(next_table)

    # Fallback: inspect all tables and pick ones with job-like headers.
    for table in soup.find_all("table"):
        header_text = clean_text(table.get_text(" ", strip=True)).lower()
        if any(key in header_text for key in ["job", "position", "salary", "location"]):
            if table not in candidate_tables:
                candidate_tables.append(table)

    for table in candidate_tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue

            values = row_to_cells(row)
            title = values[0] if values else ""
            if not title or "job title" in title.lower():
                continue

            job = {
                "title": title,
                "dept": "DLNR",
                "location": values[1] if len(values) > 1 and values[1] else "See Listing",
                "salary": values[2] if len(values) > 2 and values[2] else "See Listing",
                "link": extract_link_from_cell(cells[0], base_url),
                "source": "dlnr",
            }
            jobs.append(job)

        if jobs:
            break

    return jobs


def parse_rcuh_section(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []

    # Strategy 1: explicit RCUH section heading then parse nearby links/rows.
    rcuh_heading = soup.find(
        lambda tag: tag.name in {"h2", "h3", "h4"}
        and "rcuh" in clean_text(tag.get_text()).lower()
    )

    search_scopes: list[Any] = []
    if rcuh_heading:
        section = rcuh_heading.find_parent(["section", "div", "article"]) or rcuh_heading
        search_scopes.append(section)

    # Strategy 2 fallback: entire page, filter to links mentioning RCUH.
    search_scopes.append(soup)

    seen_links: set[str] = set()
    for scope in search_scopes:
        for anchor in scope.find_all("a", href=True):
            label = clean_text(anchor.get_text(" ", strip=True))
            href = urljoin(base_url, anchor["href"])
            blob = f"{label} {href}".lower()

            if "rcuh" not in blob:
                continue
            if href in seen_links:
                continue

            seen_links.add(href)
            jobs.append(
                {
                    "title": label or "RCUH Position",
                    "id": "See Listing",
                    "project": "RCUH",
                    "closing": "See Listing",
                    "link": href,
                    "source": "dlnr",
                }
            )

        if jobs:
            break

    return jobs


def scrape_all() -> dict[str, Any]:
    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "civil_service": [],
        "rcuh": [],
        "errors": [],
    }

    try:
        html = fetch_html(DLNR_JOBS_URL)
        soup = build_soup(html)

        result["civil_service"] = parse_civil_service_table(soup, DLNR_JOBS_URL)
        result["rcuh"] = parse_rcuh_section(soup, DLNR_JOBS_URL)

        logging.info("Civil Service rows: %s", len(result["civil_service"]))
        logging.info("RCUH rows: %s", len(result["rcuh"]))
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"dlnr_jobs_page: {type(exc).__name__}: {exc}")
        logging.warning("Failed to scrape DLNR jobs page: %s", exc)

    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = scrape_all()
    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    if data["errors"]:
        logging.warning("Completed with errors: %s", "; ".join(data["errors"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
