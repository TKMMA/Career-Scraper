import json
import re
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def clean_text(text):
    """Converts SHOUTING CAPS to Title Case."""
    if not text: return ""
    # Capitalize first letter of each word, handle special cases like DLNR
    cleaned = text.title().replace("Dlnr", "DLNR").replace("Rcuh", "RCUH")
    return cleaned.strip()

def extract_location_and_clean_title(title):
    """Extracts island/location from title and returns (Location, CleanTitle)."""
    # Look for island names preceded by a dash or space
    loc_match = re.search(r'-\s*(OAHU|MAUI|KAUAI|KONA|HILO|HAWAII|MOLOKAI|LANAI|LIHUE)\s*$', title, re.IGNORECASE)
    location = "Hawaii"
    clean_title = title
    
    if loc_match:
        location = loc_match.group(1).upper()
        clean_title = title[:loc_match.start()].strip(" -")
    
    return location, clean_text(clean_title)

def clean_salary(desc_text):
    match = re.search(r'(\$\d{1,3}(?:,\d{3})*(?:\s+to\s+\$\d{1,3}(?:,\d{3})*)?)\s+per\s+(month|year)', desc_text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} per {match.group(2).lower()}"
    return "See Listing"

def main():
    payload = {"civil_service": [], "rcuh": [], "generated_at_utc": now_iso(), "errors": []}
    ns = {'joblisting': 'http://www.neogov.com/namespaces/JobListing'}

    try:
        response = requests.get(FEED_URL, timeout=40)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        
        for item in root.findall("./channel/item"):
            dept_tag = item.find("joblisting:department", ns)
            dept_name = dept_tag.text if dept_tag is not None else ""

            if "Land & Natural Resources" in dept_name or "DLNR" in dept_name:
                raw_title = (item.findtext("title") or "").strip()
                location, title = extract_location_and_clean_title(raw_title)
                
                # Get the Posting Date (pubDate)
                pub_date_raw = item.findtext("pubDate")
                posting_date = ""
                if pub_date_raw:
                    # Formats "Mon, 23 Feb 2026..." into "Feb 23, 2026"
                    dt = datetime.strptime(pub_date_raw[:16], "%a, %d %b %Y")
                    posting_date = dt.strftime("%b %d, %Y")

                payload["civil_service"].append({
                    "title": title,
                    "job_number": item.findtext("joblisting:jobNumberSingle", namespaces=ns) or "N/A",
                    "division": clean_text(item.findtext("joblisting:division", namespaces=ns) or "DLNR"),
                    "location": location,
                    "salary": clean_salary(item.findtext("description") or ""),
                    "posted": posting_date,
                    "closing": item.findtext("joblisting:advertiseToDateTime", namespaces=ns) or "Continuous",
                    "link": (item.findtext("link") or "").strip()
                })
    except Exception as e:
        payload["errors"].append(f"Scrape error: {str(e)}")

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
