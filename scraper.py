import json
import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

CIVIL_SERVICE_URL = (
    "https://www.governmentjobs.com/careers/hawaii"
    "?department[0]=Land%20%26%20Natural%20Resources&sort=PositionTitle%7CAscending"
)
RCUH_URL = (
    "https://hr.rcuh.com/psc/hcmprd_exapp/EMPLOYEE/HRMS/c/"
    "HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?Page=HRS_APP_SCHJOB_FL&Action=U"
)
INDEED_RSS_URL = "https://www.indeed.com/rss"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}
TIMEOUT_SECONDS = 45


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def find_first(patterns: list[str], text: str, default: str = "") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return strip_tags(match.group(1))
    return default


def scrape_civil_service() -> list[dict[str, str]]:
    html = fetch_page(CIVIL_SERVICE_URL)

    item_blocks = re.findall(
        r'(<(?:tr|div)[^>]*(?:job-listing-item|class="[^"]*job-table-row[^"]*")[\s\S]*?</(?:tr|div)>)',
        html,
        flags=re.IGNORECASE,
    )
    if not item_blocks:
        item_blocks = re.findall(r"(<tr[^>]*>[\s\S]*?</tr>)", html, flags=re.IGNORECASE)

    jobs: list[dict[str, str]] = []
    for block in item_blocks:
        title = find_first(
            [
                r'class="[^"]*job-item-title[^"]*"[^>]*>([\s\S]*?)</',
                r"<td[^>]*class=\"[^\"]*title[^\"]*\"[^>]*>([\s\S]*?)</td>",
                r"<a[^>]*>([\s\S]*?)</a>",
            ],
            block,
        )
        if not title:
            continue

        link_match = re.search(r'<a[^>]*href="([^"]+)"', block, flags=re.IGNORECASE)
        link = link_match.group(1) if link_match else CIVIL_SERVICE_URL
        if link.startswith("/"):
            link = f"https://www.governmentjobs.com{link}"

        jobs.append(
            {
                "title": title,
                "dept": find_first(
                    [
                        r'class="[^"]*job-department[^"]*"[^>]*>([\s\S]*?)</',
                        r"<td[^>]*class=\"[^\"]*department[^\"]*\"[^>]*>([\s\S]*?)</td>",
                    ],
                    block,
                    "DLNR",
                ),
                "location": find_first(
                    [
                        r'class="[^"]*job-location[^"]*"[^>]*>([\s\S]*?)</',
                        r"<td[^>]*class=\"[^\"]*location[^\"]*\"[^>]*>([\s\S]*?)</td>",
                    ],
                    block,
                    "See Listing",
                ),
                "salary": find_first(
                    [
                        r'class="[^"]*job-salary[^"]*"[^>]*>([\s\S]*?)</',
                        r"<td[^>]*class=\"[^\"]*salary[^\"]*\"[^>]*>([\s\S]*?)</td>",
                    ],
                    block,
                    "See Position Description",
                ),
                "link": link,
                "source": "governmentjobs",
            }
        )

    return jobs


def scrape_rcuh() -> list[dict[str, str]]:
    html = fetch_page(RCUH_URL)

    jobs: list[dict[str, str]] = []
    title_matches = re.findall(r'id="[^"]*SCH_JOB_TITLE[^"]*"[^>]*>([\s\S]*?)<', html, flags=re.IGNORECASE)
    id_matches = re.findall(r'id="[^"]*SCH_JOB_ID[^"]*"[^>]*>([\s\S]*?)<', html, flags=re.IGNORECASE)

    for idx, raw_title in enumerate(title_matches):
        title = strip_tags(raw_title)
        if not title:
            continue
        job_id = strip_tags(id_matches[idx]) if idx < len(id_matches) else "See Listing"
        jobs.append(
            {
                "title": title,
                "id": job_id,
                "project": "RCUH",
                "closing": "See Listing",
                "link": RCUH_URL,
                "source": "rcuh",
            }
        )

    return jobs


def scrape_indeed_rss(query: str, location: str = "Hawaii") -> list[dict[str, str]]:
    url = f"{INDEED_RSS_URL}?q={quote_plus(query)}&l={quote_plus(location)}"
    xml_text = fetch_page(url)
    root = ElementTree.fromstring(xml_text)

    jobs: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip() or "https://www.indeed.com"
        company = (item.findtext("author") or "Indeed").strip()
        description = strip_tags(item.findtext("description") or "")
        if not title:
            continue
        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "link": link,
                "source": "indeed",
            }
        )

    return jobs


def apply_indeed_fallback(results: dict[str, Any]) -> None:
    if not results["civil_service"]:
        try:
            indeed_civil = scrape_indeed_rss("Hawaii Land Natural Resources civil service")
            for job in indeed_civil:
                results["civil_service"].append(
                    {
                        "title": job["title"],
                        "dept": job["company"],
                        "location": job["location"],
                        "salary": "See Listing",
                        "link": job["link"],
                        "source": "indeed",
                    }
                )
            if indeed_civil:
                results["fallbacks"].append("civil_service: indeed")
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"civil_service_indeed_fallback: {type(exc).__name__}: {exc}")

    if not results["rcuh"]:
        try:
            indeed_rcuh = scrape_indeed_rss("Research Corporation University of Hawaii RCUH")
            for job in indeed_rcuh:
                results["rcuh"].append(
                    {
                        "title": job["title"],
                        "id": "Indeed",
                        "project": job["company"],
                        "closing": "See Listing",
                        "link": job["link"],
                        "source": "indeed",
                    }
                )
            if indeed_rcuh:
                results["fallbacks"].append("rcuh: indeed")
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"rcuh_indeed_fallback: {type(exc).__name__}: {exc}")


def scrape_all() -> dict[str, Any]:
    results: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "civil_service": [],
        "rcuh": [],
        "errors": [],
        "fallbacks": [],
    }

    for name, scraper in (("civil_service", scrape_civil_service), ("rcuh", scrape_rcuh)):
        try:
            results[name] = scraper()
            logging.info("Scraped %s records from %s", len(results[name]), name)
        except Exception as exc:  # noqa: BLE001
            message = f"{name}: {type(exc).__name__}: {exc}"
            logging.warning("Failed scrape for %s: %s", name, exc)
            results["errors"].append(message)

    apply_indeed_fallback(results)
    return results


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    results = scrape_all()

    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    if results["errors"]:
        logging.warning("Completed with errors: %s", "; ".join(results["errors"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
