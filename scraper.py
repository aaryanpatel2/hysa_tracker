import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from collections import Counter, defaultdict
import re
import time
import dotenv
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

dotenv.load_dotenv()

HISTORY_FILE = 'data/history.json'
LAST_RATES_FILE = 'data/last_rates.json'
MARKET_RATES_HISTORY_FILE = 'data/market_rates_history.json'
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Notification Configuration
# Options: "always", "smart", "weekly", "monthly", "never"
NOTIFICATION_MODE = os.getenv('NOTIFICATION_MODE', 'smart')

# Smart notification thresholds
SIGNIFICANT_DROP_THRESHOLD = 0.15  # Alert if tracked bank drops by 0.15% or more
SIGNIFICANT_RISE_THRESHOLD = 0.20  # Alert if competitor rises 0.20% above best
NEW_TOP_COMPETITOR_THRESHOLD = 0.10  # Alert if new bank enters within 0.10% of best

# Define main tracked banks (for history and analysis)
MAIN_TRACKED_BANKS = ["Ally", "Sofi", "Capital One", "Marcus", "Barclays", "Apple", "Amex"]

# Define supplementary banks (scraped directly but not in main tracking)
SUPPLEMENTARY_BANKS = ["Wealthfront", "Betterment"]

# Define which banks require Selenium vs static HTML
SELENIUM_BANKS = ["Ally", "Sofi", "Capital One", "Marcus", "Amex", "Betterment"]
STATIC_BANKS = ["Wealthfront", "Barclays", "Apple"]

LINKS = {
    "Ally": "https://www.ally.com/bank/online-savings-account/?CP=ppc-google-bkws-dep-osa-high-yield-savings&source=Paid-Search-Web&d=c&ad=786445454317&gclsrc=aw.ds&gad_source=1&gad_campaignid=23323306552&gbraid=0AAAAAD06c9p7oxrieLdVq3tUSmWjOIoZg&gclid=Cj0KCQiAyP3KBhD9ARIsAAJLnnaSvS1j6x0x1rbfQTFSoPPvS3zfhj0YF0rbuuiwO57290ImCAP9HooaAnaMEALw_wcB",
    "Sofi": "https://www.sofi.com/banking/savings-account/?campaign=MRKT_SEM_MCI_MON_BRAPLUS_ACQ_EXT_ALL_tCPA_E400_20241018_BANKING-SAVINGS_PSE_GOG_NONE_US_EN_SFrvp01jxcs2gykuhsx880_e_g_c_719673685616_sofi%20hysa&utm_source=MRKT_ADWORDS&utm_medium=SEM&utm_campaign=MRKT_SEM_MCI_MON_BRAPLUS_ACQ_EXT_ALL_tCPA_E400_20241018_BANKING-SAVINGS_PSE_GOG_NONE_US_EN_SFrvp01jxcs2gykuhsx880_e_g_c_719673685616_sofi%20hysa&cl_vend=google&cl_ch=sem&cl_camp=21828358234&cl_adg=173560417150&cl_crtv=719673685616&cl_kw=sofi%20hysa&cl_pub=google.com&cl_place=&cl_dvt=c&cl_pos=&cl_mt=e&cl_gtid=kwd-1657720290178&opti_ca=21828358234&opti_ag=173560417150&opti_ad=719673685616&opti_key=kwd-1657720290178&gclid=Cj0KCQiAyP3KBhD9ARIsAAJLnnYoSpzop_WcGE43gS_GSsMUPM91zRPqgyFawVo6vt9W5aFT8TDVSfMaAlFYEALw_wcB&adname=&gclsrc=aw.ds&gad_source=1&gad_campaignid=21828358234&gbraid=0AAAAADlA3c0QHObu0w6b0MT2I_R97mCnk#2",
    "Capital One": "https://www.capitalone.com/bank/savings-accounts/online-performance-savings-account/?gclsrc=aw.ds&gad_source=1&gad_campaignid=23350992191&gbraid=0AAAAADtpBjeVFPsiqzh_12qEx3pSa0NyZ&gclid=Cj0KCQiAyP3KBhD9ARIsAAJLnnbB8dUxjgHb-nNKFQy817692dM9ciMoCIjYBEraM_DwyhUDxrDPfHkaAoszEALw_wcB",
    "Marcus": "https://www.marcus.com/us/en/savings/high-yield-savings?prd=os&chl=ps&schl=psg&cid=1897658850&agp=134193963729&gclsrc=aw.ds&gad_source=1&gad_campaignid=1897658850&gbraid=0AAAAACy1HVIfp6lcgzWcb6Ox2E0T9khTS&gclid=Cj0KCQiAyP3KBhD9ARIsAAJLnnb9F4vc8a0P-6akWwAlDfC8q9eYYMah7Vis3ISr5ImpS1VYONIMwF0aAqLFEALw_wcB",
    "Wealthfront": "https://www.wealthfront.com/cash",
    "Barclays": "https://banking.us.barclays/tiered-savings.html?refid=BBDOUOUTO01",
    "Apple": "https://learn.applecard.apple/savings?itscg=20201&itsct=crd-sem-161058037174-754940832708&mttnsubad=crd-sem-161058037174-754940832708&mttnsubkw=kwd-647220239413&mttnsubplmnt=c_adext:&mttnagencyid=c1a&mttncc=US&mttnpid=Google%20AdWords&cid=apy-318-100000070000-400000000000041",
    "Amex": "https://www.americanexpress.com/en-us/banking/online-savings/high-yield-savings-account/?eep=81153&extlink=as=search_br=GGL=14869360742_136053249799_475163951998_686081261976&gclsrc=aw.ds&gad_source=1&gad_campaignid=14869360742&gbraid=0AAAAAClSvJV_UXcyplnb3qVQmlwvIYS1W&gclid=Cj0KCQiAyP3KBhD9ARIsAAJLnna93Hf-vIOl-LM_QC6XEM9kLf_qAK-IMrWjG80HBCCxcvlWVq59QiwaAmE0EALw_wcB",
    "Betterment": "https://www.betterment.com/cash-reserve"
}

# Aggregate rate comparison sites
AGGREGATE_SOURCES = [
    "https://www.investopedia.com/high-yield-savings-accounts-4770633",
    "https://www.bankrate.com/banking/savings/best-high-yield-interests-savings-accounts/"
]

# Bank name variations - helps match banks on aggregate sites
BANK_ALIASES = {
    "Marcus": ["Marcus", "Marcus by Goldman Sachs", "Goldman Sachs"],
    "Amex": ["Amex", "American Express", "AmEx"],
    "UFB": ["UFB", "UFB Direct"],
    "Bread Savings": ["Bread Savings", "Bread Financial"],
    "Bask Bank": ["Bask Bank", "Bask"],
    "Capital One": ["Capital One", "Capital One 360", "C1"],
    "My Banking Direct": ["My Banking Direct", "MyBankingDirect"],
    "Everbank": ["Everbank", "EverBank", "EverBank Performance"],
    "Vio": ["Vio", "Vio Bank", "VioBank"],
    "Jenius": ["Jenius", "Jenius Bank"]
}

def extract_rate(text):
    """Extract APY percentage from text."""
    # Look for patterns like "4.35%", "4.35% APY", etc.
    pattern = r'(\d+\.\d+)%?'
    matches = re.findall(pattern, text)
    if matches:
        # Return the first match as float, typically the highest/most prominent
        return float(matches[0])
    return None

def scrape_ally_page(bank_name, url, driver=None):
    """Ally requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # If driver provided, skip static HTML and use it directly
        if driver is not None:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                # Find all elements with the target class
                rate_elems = wait.until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, 'span.allysf-rates-v1-value')
                )
                for idx, rate_elem in enumerate(rate_elems):
                    rate_text = rate_elem.text.strip()
                    rate = extract_rate(rate_text)
                    if rate and 0.1 <= rate <= 10:
                        print(f"✓ Selenium scrape successful (element {idx+1}): {rate}%")
                        return rate
                print(f"✗ Could not extract valid rate from any matching element.")
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback)
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find all rate elements with the specific class
        rate_elems = soup.find_all('span', class_='allysf-rates-v1-value')
        for idx, rate_elem in enumerate(rate_elems):
            rate_text = rate_elem.get_text(strip=True)
            rate = extract_rate(rate_text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful (element {idx+1}): {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            # Find all elements with the target class
            rate_elems = wait.until(
                lambda d: d.find_elements(By.CSS_SELECTOR, 'span.allysf-rates-v1-value')
            )
            found_valid = False
            for idx, rate_elem in enumerate(rate_elems):
                rate_text = rate_elem.text.strip()
                print(f"Found element {idx+1} with Selenium. Text: '{rate_text}'")
                rate = extract_rate(rate_text)
                if rate and 0.1 <= rate <= 10:
                    print(f"✓ Selenium scrape successful (element {idx+1}): {rate}%")
                    found_valid = True
                    driver.quit()
                    return rate
            if not found_valid:
                print(f"✗ Could not extract valid rate from any matching element.")
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                h2_elements = driver.find_elements(By.TAG_NAME, 'h2')
                for elem in h2_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_sofi_page(bank_name, url, driver=None):
    """Sofi requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # If driver provided, skip static HTML and use it directly
        if driver is not None:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.XPATH, "//p/strong[contains(text(), 'SoFi Plus members can earn up to')]")
))
                strong_elems = driver.find_elements(By.XPATH, "//p/strong")
                for strong in strong_elems:
                    text = strong.text
                    if "SoFi Plus members can earn up to" in text:
                        rates = re.findall(r'(\d+\.\d+)', text)
                        if rates:
                            rate = float(rates[2]) if len(rates) > 2 else float(rates[0])
                            if 0.1 <= rate <= 10:
                                print(f"✓ Selenium scrape successful: {rate}%")
                                return rate
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback)
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for p in soup.find_all('p'):
            strong = p.find('strong')
            if strong and "SoFi Plus members can earn up to" in strong.get_text():
                text = strong.get_text()
                # Find all rates in the text
                rates = re.findall(r'(\d+\.\d+)', text)
                if rates:
                    # The "current Savings APY" is usually the second number
                    if len(rates) > 1:
                        rate = float(rates[1])
                    else:
                        rate = float(rates[0])
                    if 0.1 <= rate <= 10:
                        print(f"✓ Static scrape successful: {rate}%")
                        return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.XPATH, "//p/strong[contains(text(), 'SoFi Plus members can earn up to')]")))
            # Find all <strong> tags inside <p> tags
            strong_elems = driver.find_elements(By.XPATH, "//p/strong")
            for strong in strong_elems:
                text = strong.text
                if "SoFi Plus members can earn up to" in text:
                    rates = re.findall(r'(\d+\.\d+)', text)
                    if rates:
                        # The "current Savings APY" is usually the second number
                        rate = float(rates[2]) if len(rates) > 1 else float(rates[0])
                        if 0.1 <= rate <= 10:
                            print(f"✓ Selenium scrape successful: {rate}%")
                            driver.quit()
                            return rate
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any h2 with APY text
                h2_elements = driver.find_elements(By.TAG_NAME, 'h2')
                for elem in h2_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_capitalone_page(bank_name, url, driver=None):
    """Capital One requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # If driver provided, skip static HTML and use it directly
        if driver is not None:
            try:
                wait = WebDriverWait(driver, 10)
                driver.get(url)
                rate_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'rates-inline[rate-type="APY"]'))
                )
                rate_text = rate_elem.text.strip()
                rate = extract_rate(rate_text)
                if rate and 0.1 <= rate <= 10:
                    print(f"✓ Selenium scrape successful: {rate}%")
                    return rate
                else:
                    print(f"✗ Could not extract valid rate from text: '{rate_text}'")
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback)
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element with the specific class
        rate_elem = soup.find('rates-inline', {'rate-type': 'APY'})
        
        if rate_elem:
            rate_text = rate_elem.get_text(strip=True)
            rate = extract_rate(rate_text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful: {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector instead of CLASS_NAME for compound classes
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'rates-inline[rate-type="APY"]'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any rates-inline with APY text
                rates_inline_elements = driver.find_elements(By.CSS_SELECTOR, 'rates-inline[rate-type="APY"]')
                for elem in rates_inline_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_marcus_page(bank_name, url, driver=None):
    """Marcus always requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}... (Selenium-only)")
        
        # If driver provided, use it directly
        if driver is not None:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                rate_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span[style*="font-size: 46.0px"]'))
                )
                rate_text = rate_elem.text.strip()
                apy_elem = rate_elem.find_element(By.XPATH, 'following-sibling::span[contains(text(), "APY")]')
                if apy_elem:
                    rate = extract_rate(rate_text)
                    if rate and 0.1 <= rate <= 10:
                        print(f"✓ Selenium scrape successful: {rate}%")
                        return rate
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback - creates own driver)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(url)
            # Wait for the large rate span to appear
            wait = WebDriverWait(driver, 10)
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[style*="font-size: 46.0px"]'))
            )
            rate_text = rate_elem.text.strip()
            # Optionally check for APY in the next sibling
            apy_elem = rate_elem.find_element(By.XPATH, 'following-sibling::span[contains(text(), "APY")]')
            if apy_elem:
                rate = extract_rate(rate_text)
                if rate and 0.1 <= rate <= 10:
                    print(f"✓ Selenium scrape successful: {rate}%")
                    driver.quit()
                    return rate
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
        finally:
            driver.quit()
        return None
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_barclays_page(bank_name, url):
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element with the specific class
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            for i, cell in enumerate(cells):
                if "Less than $10,000" in cell.get_text():
                    # Get the next <td> (the rate)
                    if i + 1 < len(cells):
                        rate_text = cells[i + 1].get_text(strip=True)
                        rate = extract_rate(rate_text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Static scrape successful: {rate}%")
                            return rate
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector instead of CLASS_NAME for compound classes
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'td:contains("Less than $10,000") + td'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                
                # Look for any td with APY text
                td_elements = driver.find_elements(By.TAG_NAME, 'td')
                for elem in td_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_apple_page(bank_name, url):
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element with the specific class
        for p in soup.find_all('p', class_='typography-intro'):
            text = p.get_text(" ", strip=True)  # get all text, including from children, as a single string
            rate = extract_rate(text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful: {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector instead of CLASS_NAME for compound classes
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'p.typography-intro'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any p with APY text
                p_elements = driver.find_elements(By.TAG_NAME, 'p')
                for elem in p_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_amex_page(bank_name, url, driver=None):
    """Amex requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # If driver provided, skip static HTML and use it directly
        if driver is not None:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                rate_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.axp-us-consumer-banking__index__rate___botMw'))
                )
                rate_text = rate_elem.text.strip()
                rate = extract_rate(rate_text)
                if rate and 0.1 <= rate <= 10:
                    print(f"✓ Selenium scrape successful: {rate}%")
                    return rate
                else:
                    print(f"✗ Could not extract valid rate from text: '{rate_text}'")
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback)
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element with the specific class
        rate_elem = soup.find('h2', class_='axp-us-consumer-banking__index__rate___botMw')
        
        if rate_elem:
            rate_text = rate_elem.get_text(strip=True)
            rate = extract_rate(rate_text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful: {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector instead of CLASS_NAME for compound classes
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.axp-us-consumer-banking__index__rate___botMw'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any h2 with APY text
                h2_elements = driver.find_elements(By.TAG_NAME, 'h2')
                for elem in h2_elements:
                    text = elem.text.strip()
                    if '%' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_wealthfront_page(bank_name, url):
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element with data-testid="dynamic-yields-table"
        rate_elem = soup.find('p', {'data-testid': 'dynamic-yields-table'})
        
        if rate_elem:
            rate_text = rate_elem.get_text(strip=True)
            rate = extract_rate(rate_text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful: {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector for data-testid attribute
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'p[data-testid="dynamic-yields-table"]'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any p with APY text
                p_elements = driver.find_elements(By.TAG_NAME, 'p')
                for elem in p_elements:
                    text = elem.text.strip()
                    if '%' in text and 'APY' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_betterment_page(bank_name, url, driver=None):
    """Betterment requires Selenium - can accept reused driver for efficiency"""
    try:
        print(f"Attempting to scrape {bank_name}...")
        
        # If driver provided, skip static HTML and use it directly
        if driver is not None:
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                rate_elem = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.item-title'))
                )
                rate_text = rate_elem.text.strip()
                rate = extract_rate(rate_text)
                if rate and 0.1 <= rate <= 10:
                    print(f"✓ Selenium scrape successful: {rate}%")
                    return rate
                else:
                    print(f"✗ Could not extract valid rate from text: '{rate_text}'")
            except Exception as e:
                print(f"✗ Selenium error: {str(e)}")
            return None
        
        # Original code path if no driver provided (fallback)
        # Try static HTML first
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find rate element - h1 with class="item-title"
        rate_elem = soup.find('h1', class_='item-title')
        
        if rate_elem:
            rate_text = rate_elem.get_text(strip=True)
            rate = extract_rate(rate_text)
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Static scrape successful: {rate}%")
                return rate
        
        # If static scraping failed, use Selenium
        print("Static HTML didn't work, trying Selenium with JavaScript rendering...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            
            # Wait up to 10 seconds for the rate element to appear
            wait = WebDriverWait(driver, 10)
            
            # Use CSS selector for h1.item-title
            rate_elem = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.item-title'))
            )
            
            rate_text = rate_elem.text.strip()
            print(f"Found element with Selenium. Text: '{rate_text}'")
            
            rate = extract_rate(rate_text)
            
            if rate and 0.1 <= rate <= 10:
                print(f"✓ Selenium scrape successful: {rate}%")
                driver.quit()
                return rate
            else:
                print(f"✗ Could not extract valid rate from text: '{rate_text}'")
                
        except Exception as e:
            print(f"✗ Selenium error: {str(e)}")
            # Try alternative selectors
            try:
                print("Trying alternative selector strategies...")
                # Look for any h1 with APY text
                h1_elements = driver.find_elements(By.TAG_NAME, 'h1')
                for elem in h1_elements:
                    text = elem.text.strip()
                    if '%' in text and 'APY' in text:
                        rate = extract_rate(text)
                        if rate and 0.1 <= rate <= 10:
                            print(f"✓ Found rate via alternative method: {rate}%")
                            driver.quit()
                            return rate
            except:
                pass
        finally:
            driver.quit()
        
        return None
        
    except Exception as e:
        print(f"✗ Error scraping {bank_name}: {str(e)}")
        return None

def scrape_investopedia(scraped_banks):
    """Scrape ALL rates from Investopedia."""
    my_banks = {}  # Banks from LINKS
    other_banks = {}  # Other banks not in LINKS
    failed = []
    
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(AGGREGATE_SOURCES[0], headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all list items with bank data
        # Look for <li> elements that contain both a link and a strong tag with APY
        list_items = soup.find_all('li')
        
        for item in list_items:
            # Look for bank name in <a> tag
            link = item.find('a')
            if not link:
                continue
            
            bank_name = link.get_text(strip=True)
            
            # Look for APY in <strong> tag
            strong_tags = item.find_all('strong')
            rate = None
            
            for strong in strong_tags:
                text = strong.get_text(strip=True)
                if 'APY' in text:
                    # Extract rate like "4.05% APY"
                    rate_match = re.search(r'(\d+\.\d+)%', text)
                    if rate_match:
                        rate = float(rate_match.group(1))
                        break
            
            if rate and 0.1 <= rate <= 10:
                # Check if this matches any of tracked banks
                matched = False
                for my_bank in LINKS.keys():
                    if my_bank in scraped_banks:
                        continue
                    
                    aliases = BANK_ALIASES.get(my_bank, [my_bank])
                    for alias in aliases:
                        if alias.lower() in bank_name.lower():
                            my_banks[my_bank] = rate
                            print(f"    Found {my_bank} (as '{bank_name}'): {rate}%")
                            matched = True
                            break
                    if matched:
                        break
                
                # If not matched to my banks, add to other banks
                if not matched:
                    other_banks[bank_name] = rate
        
        print(f"    Investopedia: {len(my_banks)} tracked banks, {len(other_banks)} other banks")
        
    except Exception as e:
        print(f"Error scraping Investopedia: {str(e)}")
        failed.append("Investopedia")
    
    return my_banks, other_banks, failed

def scrape_bankrate(scraped_banks):
    """Scrape ALL rates from Bankrate."""
    my_banks = {}  # Banks from LINKS
    other_banks = {}  # Other banks not in LINKS
    failed = []
    try:
        print("Using Selenium to fetch Bankrate page...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(AGGREGATE_SOURCES[1])
        
        # Wait for initial cards to load
        WebDriverWait(driver, 15).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, 'wrt-RateCard-content')) > 0
        )
        
        # Click "See more rates" button repeatedly until all cards are loaded
        max_attempts = 25  # Prevent infinite loop
        attempt = 0
        previous_count = 0
        
        while attempt < max_attempts:
            current_count = len(driver.find_elements(By.CLASS_NAME, 'wrt-RateCard-content'))
            print(f"  Currently loaded {current_count} cards...")
            
            # If no new cards loaded, we're done
            if current_count == previous_count and previous_count > 0:
                print(f"  No more cards to load. Total: {current_count}")
                break
            
            previous_count = current_count
            
            # Try to find and click the "See more" button
            try:
                # Look for button with the specific class
                see_more_button = driver.find_element(By.CLASS_NAME, 'wrt-ShowMore-button')
                
                # Check if button is visible and enabled
                if see_more_button.is_displayed() and see_more_button.is_enabled():
                    # Scroll to button and click it
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", see_more_button)
                    time.sleep(1)  # Wait for scroll
                    
                    # Click using JavaScript to avoid any interception issues
                    driver.execute_script("arguments[0].click();", see_more_button)
                    print(f"  Clicked 'See more rates' button...")
                    
                    # Wait for new cards to load
                    time.sleep(2)
                else:
                    print(f"  'See more' button not clickable. Finished loading.")
                    break
                
            except Exception as e:
                # No more "See more" button found, we've loaded everything
                print(f"  No 'See more' button found. Finished loading all cards.")
                break
            
            attempt += 1
        
        html = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html, 'html.parser')

        # Find all rate cards
        cards = soup.find_all('div', class_='wrt-RateCard-content')
        print(f"Found {len(cards)} .wrt-RateCard-content cards")
        
        for card in cards:
            # Try to get bank name from logo alt or label
            bank_name = None
            logo_img = card.find('img', class_='wrt-AdvertiserLogo-img')
            if logo_img and logo_img.has_attr('alt'):
                bank_name = logo_img['alt'].strip()
            if not bank_name:
                label = card.find('p', class_='wrt-RateCard-advertiserLabel')
                if label:
                    bank_name = label.get_text(strip=True)
            if not bank_name:
                print("  ⚠️ Skipping card: No bank name found")
                continue
            bank_name = re.sub(r'[®™]', '', bank_name).strip()
            print(f"  Processing bank: {bank_name}")

            # Find APY value - need to find the first wrt-Stat that contains APY label
            rate = None
            stats = card.find_all('div', class_='wrt-Stat')
            for stat in stats:
                label_elem = stat.find('div', class_='wrt-Stat-label')
                if label_elem and 'APY' in label_elem.get_text():
                    rate_elem = stat.find('div', class_='wrt-Stat-amount')
                    if rate_elem:
                        # Get only direct text, not from child elements like tooltips
                        rate_text = ''.join(rate_elem.find_all(string=True, recursive=False)).strip()
                        print(f"    Found APY text: '{rate_text}'")
                        try:
                            # Remove any % signs and commas
                            rate_text_clean = rate_text.replace('%', '').replace(',', '').strip()
                            rate = float(rate_text_clean)
                            print(f"    Converted to float: {rate}")
                            break
                        except ValueError as e:
                            print(f"    ✗ Could not convert '{rate_text}' to float: {e}")
                            continue
            
            if rate and 0.1 <= rate <= 10:
                # Check if this matches any of my tracked banks
                matched = False
                for my_bank in LINKS.keys():
                    if my_bank in scraped_banks:
                        continue
                    aliases = BANK_ALIASES.get(my_bank, [my_bank])
                    for alias in aliases:
                        if alias.lower() in bank_name.lower():
                            my_banks[my_bank] = rate
                            print(f"    ✓ Matched to tracked bank: {my_bank} (as '{bank_name}'): {rate}%")
                            matched = True
                            break
                    if matched:
                        break
                if not matched:
                    other_banks[bank_name] = rate
                    print(f"    → Added to other banks: {bank_name}: {rate}%")
            else:
                if rate:
                    print(f"    ✗ Rate {rate} out of valid range")
                else:
                    print(f"    ✗ No valid APY found for {bank_name}")
        print(f"Bankrate: {len(my_banks)} tracked banks, {len(other_banks)} other banks")
    except Exception as e:
        print(f"Error scraping Bankrate: {str(e)}")
        failed.append("Bankrate")
    return my_banks, other_banks, failed

def get_analysis_report(history, days=30):
    """Calculates Consistency (#1 spot) and Stability (Mean Rate)."""
    if not history:
        return "No historical data yet."
    
    recent_history = history[-days:]
    total_entries = len(recent_history)
    
    winners = []
    rate_totals = defaultdict(list) # To store all rates for averaging
    
    for entry in recent_history:
        rates = entry['rates']
        # Find the winner for consistency
        winner = max(rates, key=rates.get)
        winners.append(winner)
        # Store rates for stability mean
        for bank, rate in rates.items():
            rate_totals[bank].append(rate)
    
    # 1. Consistency Score
    counts = Counter(winners)
    
    # 2. Stability Score (Average)
    stability_data = []
    for bank, rates_list in rate_totals.items():
        avg_rate = sum(rates_list) / len(rates_list)
        stability_data.append((bank, avg_rate))
    
    # Sort stability by highest average
    stability_data.sort(key=lambda x: x[1], reverse=True)

    report = f"\n*📊 Analysis (Last {total_entries} Snapshot(s))*\n"
    report += "------------------------------------------\n"
    
    report += "*🏆 Consistency Leaderboard (Most days at #1)*\n"
    for bank, wins in counts.most_common():
        pct = (wins / total_entries) * 100
        report += f"• {bank}: {pct:.0f}% of the time\n"

    report += "\n*⚖️ Stability Score (Average APY)*\n"
    for bank, avg in stability_data:
        report += f"• {bank}: {avg:.3f}%\n"
        
    return report

def should_send_notification(main_tracked_rates, last_rates, other_rates, mode):
    """
    Determines if a notification should be sent based on the notification mode.
    
    Modes:
    - "always": Send notification every time (daily if scheduled daily)
    - "smart": Send only when significant changes detected OR it's Sunday (weekly digest)
    - "weekly": Send only on Sundays
    - "monthly": Send only on the 1st of the month
    - "never": Never send notifications (data collection only)
    
    Returns: (should_notify: bool, reason: str)
    """
    now = datetime.now()
    
    if mode == "never":
        return False, "Notification mode set to 'never'"
    
    if mode == "always":
        return True, "Always mode - sending notification"
    
    if mode == "monthly":
        if now.day == 1:
            return True, "Monthly digest (1st of month)"
        return False, "Not the 1st of the month"
    
    if mode == "weekly":
        if now.weekday() == 6:  # Sunday = 6
            return True, "Weekly digest (Sunday)"
        return False, "Not Sunday"
    
    # Smart mode: check for significant changes or send weekly digest or monthly report
    if mode == "smart":
        reasons = []
        
        # Check for significant drops in tracked banks
        for bank, current_rate in main_tracked_rates.items():
            if bank in last_rates:
                drop = last_rates[bank] - current_rate
                if drop >= SIGNIFICANT_DROP_THRESHOLD:
                    reasons.append(f"🔴 {bank} dropped {drop:.2f}% (threshold: {SIGNIFICANT_DROP_THRESHOLD}%)")
        
        # Check for new competitive threats (banks that newly cross the threshold)
        # Only alert if a competitor wasn't a threat before but is now
        if main_tracked_rates:
            best_tracked_rate = max(main_tracked_rates.values())
            
            # Get previous market rates to compare
            previous_market_rates = {}
            try:
                if os.path.exists(MARKET_RATES_HISTORY_FILE):
                    with open(MARKET_RATES_HISTORY_FILE, 'r') as f:
                        market_history_data = json.load(f)
                        if len(market_history_data) >= 1:
                            previous_market_rates = market_history_data[-1].get("banks", {})
            except:
                pass
            
            # Only alert on new threats or significant gap increases
            for bank, rate in other_rates.items():
                current_gap = rate - best_tracked_rate
                if current_gap >= SIGNIFICANT_RISE_THRESHOLD:
                    # Check if this is a new threat (wasn't above threshold before)
                    if bank in previous_market_rates:
                        previous_gap = previous_market_rates[bank] - best_tracked_rate
                        # Only alert if gap increased by at least 0.10% or newly crossed threshold
                        if previous_gap < SIGNIFICANT_RISE_THRESHOLD or current_gap - previous_gap >= 0.10:
                            reasons.append(f"🔴 {bank} now {current_gap:.2f}% above your best (was {previous_gap:.2f}%)")
                    else:
                        # New bank we haven't seen before
                        reasons.append(f"🔴 NEW: {bank} is {current_gap:.2f}% above your best!")
        
        # Always send monthly report on 1st of month
        if now.day == 1:
            reasons.append("🟢 Monthly comprehensive report (1st of month)")
        
        # Always send weekly digest on Sunday (unless it's also the 1st - in that case avoid duplicate messages)
        if now.weekday() == 6 and now.day != 1:  # Sunday but not 1st
            reasons.append("🟡 Weekly digest (Sunday)")
        
        if reasons:
            return True, " | ".join(reasons)
        
        return False, "No significant changes detected"
    
    # Default to always if mode not recognized
    return True, f"Unknown mode '{mode}' - defaulting to always"

def run_tracker():
    if not os.path.exists('data'): 
        os.makedirs('data')
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f: 
            json.dump([], f)
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except json.JSONDecodeError:
        history = []

    # Load last rates to check for changes
    last_rates = {}
    if os.path.exists(LAST_RATES_FILE):
        try:
            with open(LAST_RATES_FILE, 'r') as f:
                last_rates = json.load(f)
        except:
            pass
    
    # Load market rates history
    market_history = []
    if os.path.exists(MARKET_RATES_HISTORY_FILE):
        try:
            with open(MARKET_RATES_HISTORY_FILE, 'r') as f:
                market_history = json.load(f)
        except:
            pass

    main_tracked_rates = {}  # Rates for main tracked banks (7 banks)
    supplementary_rates = {}  # Rates for supplementary banks (Wealthfront, Betterment)
    other_rates = {}  # Rates for other banks from aggregate sites
    failed_scrapes = []
    
    print("Starting rate scraping...")
    
    # Helper function to scrape a single static bank
    def scrape_static_bank(bank_name, url):
        """Scrape a bank that only needs static HTML"""
        print(f"Scraping {bank_name} (static)...")
        rate = None
        
        match bank_name:
            case "Wealthfront":
                rate = scrape_wealthfront_page(bank_name, url)
            case "Barclays":
                rate = scrape_barclays_page(bank_name, url)
            case "Apple":
                rate = scrape_apple_page(bank_name, url)
        
        if rate is not None:
            print(f"  ✓ {bank_name}: {rate}%")
        else:
            print(f"  ✗ {bank_name}: Failed to scrape")
        
        return bank_name, rate
    
    # 1. Scrape static banks in parallel (fast, no Selenium needed)
    static_banks_to_scrape = {bank: url for bank, url in LINKS.items() if bank in STATIC_BANKS}
    
    if static_banks_to_scrape:
        print(f"\nScraping {len(static_banks_to_scrape)} static banks in parallel...")
        with ThreadPoolExecutor(max_workers=len(static_banks_to_scrape)) as executor:
            future_to_bank = {executor.submit(scrape_static_bank, bank_name, url): bank_name 
                             for bank_name, url in static_banks_to_scrape.items()}
            
            for future in as_completed(future_to_bank):
                bank_name, rate = future.result()
                
                if rate is not None:
                    if bank_name in MAIN_TRACKED_BANKS:
                        main_tracked_rates[bank_name] = rate
                    elif bank_name in SUPPLEMENTARY_BANKS:
                        supplementary_rates[bank_name] = rate
                else:
                    if bank_name in MAIN_TRACKED_BANKS:
                        failed_scrapes.append(bank_name)
    
    # 2. Scrape Selenium banks sequentially with ONE reused driver
    selenium_banks_to_scrape = {bank: url for bank, url in LINKS.items() if bank in SELENIUM_BANKS}
    
    if selenium_banks_to_scrape:
        print(f"\nScraping {len(selenium_banks_to_scrape)} Selenium banks with reused driver...")
        
        # Create one driver for all Selenium banks
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={USER_AGENT}')
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            for bank_name, url in selenium_banks_to_scrape.items():
                print(f"Scraping {bank_name} (Selenium)...")
                rate = None
                
                match bank_name:
                    case "Ally":
                        rate = scrape_ally_page(bank_name, url, driver=driver)
                    case "Sofi":
                        rate = scrape_sofi_page(bank_name, url, driver=driver)
                    case "Capital One":
                        rate = scrape_capitalone_page(bank_name, url, driver=driver)
                    case "Marcus":
                        rate = scrape_marcus_page(bank_name, url, driver=driver)
                    case "Amex":
                        rate = scrape_amex_page(bank_name, url, driver=driver)
                    case "Betterment":
                        rate = scrape_betterment_page(bank_name, url, driver=driver)
                
                if rate is not None:
                    if bank_name in MAIN_TRACKED_BANKS:
                        main_tracked_rates[bank_name] = rate
                    elif bank_name in SUPPLEMENTARY_BANKS:
                        supplementary_rates[bank_name] = rate
                    print(f"  ✓ {bank_name}: {rate}%")
                else:
                    if bank_name in MAIN_TRACKED_BANKS:
                        failed_scrapes.append(bank_name)
                    print(f"  ✗ {bank_name}: Failed to scrape")
        finally:
            driver.quit()
            print("Closed shared Selenium driver")
    
    # 2. Scrape aggregate sources for main tracked banks that were missed and all other banks
    print("\nScraping aggregate sources...")
    
    # Investopedia
    inv_my_banks, inv_other_banks, investopedia_failed = scrape_investopedia(main_tracked_rates.keys())
    main_tracked_rates.update(inv_my_banks)
    other_rates.update(inv_other_banks)
    failed_scrapes.extend(investopedia_failed)
    
    # Bankrate
    br_my_banks, br_other_banks, bankrate_failed = scrape_bankrate(main_tracked_rates.keys())
    main_tracked_rates.update(br_my_banks)
    
    # Merge other banks (keep highest rate if duplicate)
    for bank, rate in br_other_banks.items():
        if bank not in other_rates or rate > other_rates[bank]:
            other_rates[bank] = rate
    
    failed_scrapes.extend(bankrate_failed)
    
    # Remove banks from failed_scrapes if they were found by aggregate sources
    failed_scrapes = [bank for bank in failed_scrapes if bank not in main_tracked_rates]
    
    print(f"\nMain tracked banks collected: {len(main_tracked_rates)}")
    print(f"Supplementary banks collected: {len(supplementary_rates)}")
    print(f"Other market banks found: {len(other_rates)}")
    print(f"Failed scrapes: {len(failed_scrapes)}")
    
    if not main_tracked_rates:
        print("ERROR: No rates were successfully scraped for main tracked banks!")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Save current rates to last_rates.json (main tracked banks only)
    with open(LAST_RATES_FILE, 'w') as f:
        json.dump(main_tracked_rates, f, indent=4)
    
    # Save to history (main tracked banks only)
    history.append({"date": timestamp, "rates": main_tracked_rates})
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
    
    # Save market rates history (all banks from aggregates)
    market_history.append({"date": timestamp, "banks": other_rates})
    with open(MARKET_RATES_HISTORY_FILE, 'w') as f:
        json.dump(market_history, f, indent=4)
    
    # Calculate notable mentions
    notable_mentions = []
    
    # Get previous market rates for comparison
    previous_market_rates = market_history[-2]["banks"] if len(market_history) >= 2 else {}
    
    # 1. Banks with biggest rate jumps (positive changes only)
    rate_changes = []
    for bank, rate in other_rates.items():
        if bank in previous_market_rates:
            change = rate - previous_market_rates[bank]
            if change > 0.05:  # At least 0.05% increase
                rate_changes.append((bank, rate, change))
    rate_changes.sort(key=lambda x: x[2], reverse=True)
    
    # 2. New banks that entered top 10
    sorted_other_rates = sorted(other_rates.items(), key=lambda x: x[1], reverse=True)
    new_top_banks = []
    if previous_market_rates:
        previous_top_10 = sorted(previous_market_rates.items(), key=lambda x: x[1], reverse=True)[:10]
        previous_top_10_names = [bank for bank , rate in previous_top_10]
        new_top_banks = [(bank, rate) for bank, rate in sorted_other_rates[:10] 
                        if bank not in previous_top_10_names]
    
    # 3. Banks very close to best tracked bank (within 0.10%)
    if main_tracked_rates:
        best_tracked_rate = max(main_tracked_rates.values())
        close_competitors = [(bank, rate) for bank, rate in other_rates.items() 
                           if abs(rate - best_tracked_rate) <= 0.10 and rate >= best_tracked_rate]
        close_competitors.sort(key=lambda x: x[1], reverse=True)
    else:
        close_competitors = []
    
    # Build notable mentions list
    if rate_changes[:3]:  # Top 3 biggest increases
        for bank, rate, change in rate_changes[:3]:
            notable_mentions.append(f"📈 *{bank}*: {rate:.2f}% (↑ +{change:.2f}%)")
    
    if new_top_banks:
        for bank, rate in new_top_banks[:2]:  # Show up to 2 new entrants
            notable_mentions.append(f"🆕 *{bank}*: {rate:.2f}% (New to top 10!)")
    
    if close_competitors[:2]:  # Top 2 close competitors
        for bank, rate in close_competitors[:2]:
            notable_mentions.append(f"🎯 *{bank}*: {rate:.2f}% (Within 0.10% of your best!)")

    # Build Slack Message
    msg = f"🔔 *HYSA Rate Alert - {timestamp}*\n\n"
    
    # Section 1: My Main Tracked Banks (7 banks)
    msg += f"*📌 MY TRACKED BANKS ({len(main_tracked_rates)}/{len(MAIN_TRACKED_BANKS)} banks)*\n"
    msg += "=" * 40 + "\n"
    sorted_main_rates = sorted(main_tracked_rates.items(), key=lambda x: x[1], reverse=True)
    for i, (bank, rate) in enumerate(sorted_main_rates, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        change = ""
        if bank in last_rates:
            diff = rate - last_rates[bank]
            if diff > 0:
                change = f" (↑ +{diff:.2f}%)"
            elif diff < 0:
                change = f" (↓ {diff:.2f}%)"
        msg += f"{emoji} #{i}. {bank}: {rate:.2f}%{change}\n"
    
    # Show failed scrapes if any
    if failed_scrapes:
        msg += f"\n⚠️ *Failed to scrape ({len(failed_scrapes)}):* "
        msg += ", ".join(failed_scrapes) + "\n"
    
    # Section 2: Supplementary Banks (Wealthfront, Betterment)
    if supplementary_rates:
        msg += "\n*💡 SUPPLEMENTARY BANKS (Monitoring)*\n"
        msg += "=" * 40 + "\n"
        sorted_supp_rates = sorted(supplementary_rates.items(), key=lambda x: x[1], reverse=True)
        for bank, rate in sorted_supp_rates:
            msg += f"• {bank}: {rate:.2f}%\n"
    
    # Section 3: Other Top Market Rates
    if other_rates:
        total_market_banks = len(other_rates)
        msg += f"\n*🌐 OTHER TOP MARKET RATES (Top 15 of {total_market_banks} banks)*\n"
        msg += "=" * 40 + "\n"
        sorted_other_rates = sorted(other_rates.items(), key=lambda x: x[1], reverse=True)
        for i, (bank, rate) in enumerate(sorted_other_rates[:15], 1):  # Show top 15
            msg += f"#{i}. {bank}: {rate:.2f}%\n"
        
        # Add notable mentions section if there are any
        if notable_mentions:
            msg += "\n*⭐ NOTABLE MENTIONS*\n"
            for mention in notable_mentions:
                msg += f"{mention}\n"
        
        msg += f"\n_💾 Full market data ({total_market_banks} banks) saved to {MARKET_RATES_HISTORY_FILE}_\n"
    
    # Add analysis report (only for main tracked banks)
    msg += "\n" + get_analysis_report(history)

    print("\n" + msg)
    
    # Smart notification logic
    should_notify, reason = should_send_notification(main_tracked_rates, last_rates, other_rates, NOTIFICATION_MODE)
    
    print(f"\n{'='*50}")
    print(f"Notification Mode: {NOTIFICATION_MODE}")
    print(f"Should Send: {should_notify}")
    print(f"Reason: {reason}")
    print(f"{'='*50}")
    
    if should_notify:
        if SLACK_WEBHOOK_URL:
            # Add notification reason to message if in smart mode
            if NOTIFICATION_MODE == "smart":
                msg = f"🚨 *ALERT TRIGGERED*: {reason}\n\n" + msg
            
            try:
                response = requests.post(SLACK_WEBHOOK_URL, json={"text": msg})
                print(f"\n✅ Slack notification sent! Status: {response.status_code}")
            except Exception as e:
                print(f"\n❌ Failed to send Slack notification: {str(e)}")
        else:
            print("\n⚠️ No Slack webhook configured - notification would be sent if configured")
    else:
        print(f"\n🔕 Notification suppressed: {reason}")


if __name__ == "__main__":
    run_tracker()