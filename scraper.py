import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_civil_service():
    driver = get_driver()
    url = "https://www.governmentjobs.com/careers/hawaii?department[0]=Land%20%26%20Natural%20Resources&sort=PositionTitle%7CAscending"
    jobs = []
    try:
        driver.get(url)
        # Wait for the job table to load
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "job-listing-item")))
        
        listings = driver.find_elements(By.CLASS_NAME, "job-listing-item")
        for item in listings:
            title_el = item.find_element(By.CLASS_NAME, "job-item-title")
            jobs.append({
                "title": title_el.text,
                "dept": "DLNR",
                "location": item.find_element(By.CLASS_NAME, "job-location").text,
                "salary": item.find_element(By.CLASS_NAME, "job-salary").text,
                "link": title_el.find_element(By.TAG_NAME, "a").get_attribute("href")
            })
    finally:
        driver.quit()
    return jobs

def scrape_rcuh():
    driver = get_driver()
    # Direct search link for RCUH
    url = "https://hr.rcuh.com/psc/hcmprd_exapp/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?Page=HRS_APP_SCHJOB_FL&Action=U"
    jobs = []
    try:
        driver.get(url)
        # RCUH uses iframes and deep-loading JS. 
        # We wait for the job list container to appear
        time.sleep(10) # Simple sleep to ensure Oracle PeopleSoft loads
        
        listings = driver.find_elements(By.CSS_SELECTOR, "li.ps-level1")
        for item in listings:
            try:
                title = item.find_element(By.ID, "SCH_JOB_TITLE$0").text # Simplified selector
                job_id = item.find_element(By.ID, "SCH_JOB_ID$0").text
                jobs.append({
                    "title": title,
                    "id": job_id,
                    "project": "Various",
                    "closing": "See Listing",
                    "link": url
                })
            except:
                continue
    finally:
        driver.quit()
    return jobs

if __name__ == "__main__":
    results = {
        "civil_service": scrape_civil_service(),
        "rcuh": scrape_rcuh()
    }
    
    with open("jobs.json", "w") as f:
        json.dump(results, f, indent=4)
