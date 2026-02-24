import json
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

# The official NEOGOV RSS feed for the State of Hawaii
FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def now_iso() -> str:
    """Returns the current UTC time in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def save_payload(payload: dict) -> None:
    """Saves the job data to jobs.json."""
    with open("jobs.json", "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)

def main() -> int:
    # Initialize the structure your website expects
    payload = {
        "civil_service": [],
        "rcuh": [],
        "generated_at_utc": now_iso(),
        "errors": []
    }
    
    try:
        # Fetch the RSS feed
        response = requests.get(FEED_URL, timeout=40)
        response.raise_for_status()
        
        # Parse the XML data
        root = ElementTree.fromstring(response.text)
        
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").lower()
            category = (item.findtext("category") or "").lower()
            
            if not title or not link:
                continue

            # BROAD SEARCH: Look for DLNR keywords in Title, Description, or Category
            search_blob = f"{title.lower()} {description} {category}"
            keywords = ["land & natural resources", "dlnr", "land and natural resources"]
            
            if any(word in search_blob for word in keywords):
                payload["civil_service"].append({
                    "title": title,
                    "dept": "DLNR",
                    "location": "See Listing",
                    "salary": "See Listing",
                    "link": link
                })
                
    except Exception as e:
        # If anything fails, log the error but still save the file
        payload["errors"].append(f"Scrape error: {str(e)}")

    # Update timestamp and save
    payload["generated_at_utc"] = now_iso()
    save_payload(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
