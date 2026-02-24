import json
import re
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def clean_salary(desc_text):
    """Extracts salary like '$3,606 to $4,563 per month' from description."""
    # Look for dollar patterns followed by 'month' or 'year'
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
                title = (item.findtext("title") or "").strip()
                desc_raw = item.findtext("description") or ""
                
                payload["civil_service"].append({
                    "title": title,
                    "job_number": item.findtext("joblisting:jobNumberSingle", namespaces=ns) or "N/A",
                    "dept": "DLNR",
                    "location": item.findtext("joblisting:location", namespaces=ns) or "Hawaii",
                    "salary": clean_salary(desc_raw),
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
