import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Updated headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_civil_service():
    driver = get_driver()
    url = "https://www.governmentjobs.com/careers/hawaii?department[0]=Land%20%26%20Natural%20Resources&sort=PositionTitle%7CAscending"
    jobs = []
    try:
        driver.get(url)
        # Wait for the table to actually exist
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "job-listing-item")))
        listings = driver.find_elements(By.CLASS_NAME, "job-listing-item")
        for item in listings:
            try:
                title_el = item.find_element(By.CLASS_NAME, "job-item-title")
                jobs.append({
                    "title": title_el.text,
                    "dept": "DLNR",
                    "location": item.find_element(By.CLASS_NAME, "job-location").text,
                    "salary": item.find_element(By.CLASS_NAME, "job-salary").text,
                    "link": title_el.find_element(By.TAG_NAME, "a").get_attribute("href")
                })
            except: continue
    finally:
        driver.quit()
    return jobs

def scrape_rcuh():
    driver = get_driver()
    url = "https://hr.rcuh.com/psc/hcmprd_exapp/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?Page=HRS_APP_SCHJOB_FL&Action=U"
    jobs = []
    try:
        driver.get(url)
        time.sleep(15) # RCUH/Oracle is slow to load frames
        listings = driver.find_elements(By.CSS_SELECTOR, "li.ps-level1")
        for item in listings:
            try:
                title = item.find_element(By.CSS_SELECTOR, "[id^='SCH_JOB_TITLE']").text
                job_id = item.find_element(By.CSS_SELECTOR, "[id^='SCH_JOB_ID']").text
                jobs.append({
                    "title": title,
                    "id": job_id,
                    "project": "RCUH/DLNR",
                    "closing": "See Link",
                    "link": url
                })
            except: continue
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
