import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests

NEOGOV_RSS_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"
TIMEOUT_SECONDS = 40
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}
DLNR_FILTER_TEXT = "land & natural resources"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def extract_salary(description: str) -> str:
    normalized = clean_text(description)
    match = re.search(r"salary\s*:?\s*(.+?)(?:\.|<|$)", normalized, flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))

    # Fallback for common patterns like "$5,000 - $6,000/month" appearing in description text.
    range_match = re.search(r"(\$[\d,]+(?:\.\d{2})?\s*(?:-|to)\s*\$[\d,]+(?:\.\d{2})?(?:\s*/\s*\w+)?)", normalized, flags=re.IGNORECASE)
    if range_match:
        return clean_text(range_match.group(1))

    return "See Listing"


def contains_dlnr_text(category: str, description: str) -> bool:
    haystack = f"{category} {description}".lower()
    haystack = haystack.replace("&amp;", "&")
    return DLNR_FILTER_TEXT in haystack


def fetch_feed_items() -> list[dict[str, str]]:
    response = requests.get(NEOGOV_RSS_URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    items: list[dict[str, str]] = []

    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title", default=""))
        link = clean_text(item.findtext("link", default=""))
        category = clean_text(item.findtext("category", default=""))
        description = clean_text(item.findtext("description", default=""))

        if not title or not link:
            continue

        if not contains_dlnr_text(category, description):
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "dept": "DLNR",
                "salary": extract_salary(description),
            }
        )

    return items


def build_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "civil_service": [],
        "rcuh": [],
    }

    try:
        payload["civil_service"] = fetch_feed_items()
        logging.info("Civil Service rows: %s", len(payload["civil_service"]))
    except Exception as exc:  # noqa: BLE001
        logging.warning("NEOGOV RSS fetch failed: %s", exc)

    return payload


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    payload = build_payload()
    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
