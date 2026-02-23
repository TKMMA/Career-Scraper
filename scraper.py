import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

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


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def fetch_jobs_page() -> BeautifulSoup:
    response = requests.get(DLNR_JOBS_URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_civil_service(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    Scrape the first table under the Current Openings area.
    Mapping requested by user:
      - Column 1 (date) ignored
      - Column 2 -> title + link
      - Column 3 -> id (recruitment)
    """
    table = soup.find("table")
    if table is None:
        raise ValueError("No table found on DLNR jobs page")

    jobs: list[dict[str, str]] = []

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        title_cell = cells[1]
        recruitment_cell = cells[2]

        anchor = title_cell.find("a", href=True)
        title = clean_text(anchor.get_text(" ", strip=True) if anchor else title_cell.get_text(" ", strip=True))
        if not title:
            continue

        link = urljoin(DLNR_JOBS_URL, anchor["href"]) if anchor else DLNR_JOBS_URL
        recruitment_id = clean_text(recruitment_cell.get_text(" ", strip=True)) or "See Listing"

        jobs.append(
            {
                "title": title,
                "id": recruitment_id,
                "dept": "DLNR",
                "location": "See Listing",
                "salary": "See Listing",
                "link": link,
            }
        )

    return jobs


def parse_rcuh(soup: BeautifulSoup) -> list[dict[str, str]]:
    """
    From the 'More ways to mālama Hawaiʻi' section, include links whose
    text contains RCUH or Research Corporation of the University of Hawaii.
    """
    jobs: list[dict[str, str]] = []
    seen_links: set[str] = set()

    section_heading = soup.find(
        lambda tag: tag.name in {"h2", "h3", "h4"}
        and "more ways to mālama hawai" in clean_text(tag.get_text()).lower()
    )
    scope: Any = section_heading.find_parent(["section", "div", "article"]) if section_heading else soup
    if scope is None:
        scope = soup

    for anchor in scope.find_all("a", href=True):
        label = clean_text(anchor.get_text(" ", strip=True))
        combined = label.lower()
        if "rcuh" not in combined and "research corporation of the university of hawaii" not in combined:
            continue

        link = urljoin(DLNR_JOBS_URL, anchor["href"])
        if link in seen_links:
            continue
        seen_links.add(link)

        jobs.append(
            {
                "title": label or "RCUH Position",
                "id": "See Listing",
                "project": "RCUH",
                "closing": "See Listing",
                "link": link,
            }
        )

    return jobs


def scrape_all() -> dict[str, Any]:
    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "civil_service": [],
        "rcuh": [],
        "errors": [],
    }

    try:
        soup = fetch_jobs_page()
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"dlnr_jobs_page_fetch: {type(exc).__name__}: {exc}")
        return result

    try:
        result["civil_service"] = parse_civil_service(soup)
        logging.info("Civil Service rows: %s", len(result["civil_service"]))
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"civil_service_parse: {type(exc).__name__}: {exc}")

    try:
        result["rcuh"] = parse_rcuh(soup)
        logging.info("RCUH rows: %s", len(result["rcuh"]))
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"rcuh_parse: {type(exc).__name__}: {exc}")

    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    payload = scrape_all()
    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

    if payload["errors"]:
        logging.warning("Completed with errors: %s", "; ".join(payload["errors"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
