import json
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def main():
    payload = {
        "civil_service": [],
        "rcuh": [],
        "generated_at_utc": now_iso(),
        "errors": []
    }
    
    # Define the namespaces used in the NEOGOV XML
    ns = {'joblisting': 'http://www.neogov.com/namespaces/JobListing'}

    try:
        response = requests.get(FEED_URL, timeout=40)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            
            # Target the specific Department tag in the XML
            dept_tag = item.find("joblisting:department", ns)
            dept_name = dept_tag.text if dept_tag is not None else ""
            
            # Target the Salary tag
            salary_tag = item.find("joblisting:minimumSalary", ns)
            salary = salary_tag.text if salary_tag is not None else "See Listing"

            # Check if this job belongs to DLNR
            if "Land & Natural Resources" in dept_name or "DLNR" in dept_name:
                payload["civil_service"].append({
                    "title": title,
                    "dept": "DLNR",
                    "location": item.findtext("joblisting:location", namespaces=ns) or "Hawaii",
                    "salary": salary,
                    "link": link
                })
    except Exception as e:
        payload["errors"].append(f"Scrape error: {str(e)}")

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
