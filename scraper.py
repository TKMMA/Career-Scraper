import json
import re
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def clean_text(text):
    """Converts SHOUTING CAPS to Title Case but preserves Roman Numerals and acronyms."""
    if not text: return ""
    
    # Capitalize first letter of each word
    words = text.lower().split()
    roman_numerals = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
    acronyms = ["dlnr", "rcuh", "it"]
    
    formatted_words = []
    for word in words:
        clean_word = word.strip("(),.-")
        if clean_word in roman_numerals or clean_word in acronyms:
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word.capitalize())
            
    return " ".join(formatted_words)

def extract_location_and_clean_title(title):
    """Extracts island/location from title and returns (Location, CleanTitle)."""
    # Look for island names preceded by a dash or space at the end of the string
    loc_pattern = r'[-\s]+(OAHU|MAUI|KAUAI|KONA|HILO|HAWAII|MOLOKAI|LANAI|LIHUE|STATEWIDE)\s*$'
    loc_match = re.search(loc_pattern, title, re.IGNORECASE)
    
    location = "Hawaii"
    clean_title = title
    
    if loc_match:
        location = loc_match.group(1).upper()
        # Remove the location part from the title
        clean_title = title[:loc_match.start()].strip(" -")
    
    return location, clean_text(clean_title)

def clean_salary(desc_text):
    """Regex to find salary info in description text."""
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

            # Filter for DLNR positions
            if "Land & Natural Resources" in dept_name or "DLNR" in dept_name:
                raw_title = (item.findtext("title") or "").strip()
                location, title = extract_location_and_clean_title(raw_title)
                
                # Get the Posting Date (pubDate)
                pub_date_raw = item.findtext("pubDate")
                posting_date = "N/A"
                if pub_date_raw:
                    try:
                        dt = datetime.strptime(pub_date_raw[:16], "%a, %d %b %Y")
                        posting_date = dt.strftime("%b %d, %Y")
                    except:
                        posting_date = pub_date_raw

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
