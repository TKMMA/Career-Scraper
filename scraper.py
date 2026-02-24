import json
import re
from datetime import datetime, timezone
from xml.etree import ElementTree
import requests

FEED_URL = "https://www.governmentjobs.com/SearchEngine/JobsFeed?agency=hawaii"

def clean_text(text):
    if not text: return ""
    # Strip HTML tags before processing
    text = re.sub('<[^<]+?>', '', text)
    words = text.lower().split()
    roman_numerals = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
    return " ".join(w.upper() if w in roman_numerals or w in ["dlnr", "rcuh"] else w.capitalize() for w in words)

def parse_salary_to_yearly(desc):
    """Aggressive regex to find salary in HTML-heavy descriptions."""
    # Remove HTML tags first to see plain text
    text = re.sub('<[^<]+?>', ' ', desc)
    
    # Matches patterns like "$3,000 to $4,000 per month" or "$50,000.00 per year"
    # Group 1: Min Salary, Group 2: Unit (month/year)
    pattern = r'\$\s*([\d,]+(?:\.\d+)?)(?:\s+to\s+\$\s*[\d,]+(?:\.\d+)?)?\s*per\s*(month|year|hr|hour)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        try:
            amount = float(match.group(1).replace(',', ''))
            unit = match.group(2).lower()
            if 'month' in unit: return amount * 12
            if 'yr' in unit or 'year' in unit: return amount
            if 'hr' in unit or 'hour' in unit: return amount * 2080 # Standard work year
        except: return None
    return None

def extract_location(title):
    """Splits title at '-' to pull out location and cleans both."""
    if "-" in title:
        parts = title.split("-")
        clean_title = parts[0].strip()
        location = parts[1].strip()
        return clean_text(clean_title), clean_text(location)
    return clean_text(title), "Hawaii"

def main():
    payload = {"civil_service": [], "rcuh": [], "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    ns = {'joblisting': 'http://www.neogov.com/namespaces/JobListing'}

    try:
        r = requests.get(FEED_URL, timeout=40)
        root = ElementTree.fromstring(r.content)
        for item in root.findall("./channel/item"):
            dept = item.findtext("joblisting:department", namespaces=ns) or ""
            if "Land & Natural Resources" in dept or "DLNR" in dept:
                raw_title = item.findtext("title") or ""
                clean_title, location = extract_location(raw_title)
                desc = item.findtext("description") or ""
                
                yearly = parse_salary_to_yearly(desc)
                payload["civil_service"].append({
                    "title": clean_title,
                    "job_number": item.findtext("joblisting:jobNumberSingle", namespaces=ns) or "N/A",
                    "division": clean_text(item.findtext("joblisting:division", namespaces=ns) or "DLNR"),
                    "location": location,
                    "yearly_salary": yearly,
                    "posted": item.findtext("pubDate")[:16] if item.findtext("pubDate") else "",
                    "closing": item.findtext("joblisting:advertiseToDateTime", namespaces=ns) or "Continuous",
                    "link": item.findtext("link")
                })
    except Exception as e: payload["errors"] = [str(e)]
    with open("jobs.json", "w") as f: json.dump(payload, f, indent=2)

if __name__ == "__main__": main()
