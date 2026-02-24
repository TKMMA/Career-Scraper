import json
from datetime import datetime, timezone
from xml.etree import ElementTree

import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def save_payload(payload: dict) -> None:
    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def main() -> int:
    payload = {
        "civil_service": [],
        "rcuh": [],
        "generated_at_utc": now_iso(),
    }

    try:
        response = requests.get(FEED_URL, timeout=40)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)

        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()

            if not title or not link:
                continue

            title_lower = title.lower()
            if "land" not in title_lower and "natural" not in title_lower:
                continue

            payload["civil_service"].append(
                {
                    "title": title,
                    "link": link,
                    "salary": "See Listing",
                }
            )
    except Exception:
        pass

    payload["generated_at_utc"] = now_iso()
    save_payload(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
