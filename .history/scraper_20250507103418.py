import requests
import http.cookiejar
import re
import csv
import time
import os
from datetime import datetime, timedelta
from io import StringIO

# Define the CSV file name (using relative path or memory storage for serverless deployment)
CSV_MEMORY = StringIO()  # In-memory storage for CSV data

# Delay between fetching pages
DELAY = 5  # Reduced for API usage

# Retry configuration
RETRY_COUNT = 3  # Reduced for API usage
RETRY_DELAY = 10  # Reduced for API usage

# Define START_MONTH
# None for Default to last month
START_MONTH = None  # Example: "Jan 24"

# Define END_MONTH
# None for Default to the current month
END_MONTH = None  # Example: "Mar 24"

# For scraping in a descending order
DIRECTION = -1

# File to store cookies (use temp storage for serverless)
COOKIE_FILE = "/tmp/cookies.txt" if os.path.exists("/tmp") else "cookies.txt"

def load_cookies(cookie_file):
    """Load cookies from a file."""
    cookie_jar = http.cookiejar.LWPCookieJar()
    try:
        cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
    except FileNotFoundError:
        pass  # No cookies file found, starting fresh
    return cookie_jar

def save_cookies(cookie_jar, cookie_file):
    """Save cookies to a file."""
    try:
        cookie_jar.save(cookie_file, ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print(f"Warning: Could not save cookies: {e}")

def get_search_page():
    url = "https://www.planning2.cityoflondon.gov.uk/online-applications/search.do?action=simple&searchType=Application"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.planning2.cityoflondon.gov.uk/online-applications/timeout.do",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # Load cookies and create a session
    cookie_jar = load_cookies(COOKIE_FILE)
    session = requests.Session()
    session.cookies = cookie_jar

    response = None  # Initialize response variable
    for attempt in range(RETRY_COUNT):
        try:
            # Perform the request
            response = session.get(url, headers=headers)
            
            # Check if the request was successful
            if response.ok:
                break  # Exit the loop on success
            else:
                print(f"HTTP error: {response.status_code}. Retrying {attempt + 1}/{RETRY_COUNT}...")
                time.sleep(RETRY_DELAY)  # Wait before retrying
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"Connection error: {e}. Retrying {attempt + 1}/{RETRY_COUNT}...")
            time.sleep(RETRY_DELAY)  # Wait before retrying

    # Check if the response is None, meaning all attempts failed
    if response is None or not response.ok:
        raise RuntimeError(f"Failed to fetch {url} after {RETRY_COUNT} attempts.")

    # Save cookies after the request
    save_cookies(cookie_jar, COOKIE_FILE)

    # Check for a successful request
    if response.status_code == 200:
        # Extract _csrf value using regex
        csrf_match = re.search(r'<input type="hidden" name="_csrf" value="([^"]+)" />', response.text)
        if csrf_match:
            return csrf_match.group(1)  # Return the CSRF token value
        else:
            raise Exception("CSRF token not found in the page.")
    else:
        raise Exception(f"Failed to fetch the page. Status code: {response.status_code}")

def get_first_page(csrf, search_month, _ward):
    url = "https://www.planning2.cityoflondon.gov.uk/online-applications/monthlyListResults.do?action=firstPage"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.planning2.cityoflondon.gov.uk",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.planning2.cityoflondon.gov.uk/online-applications/search.do?action=monthlyList",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # Payload for the POST request
    payload = {
        "_csrf": csrf,
        "searchCriteria.ward": _ward,
        "month": search_month,
        "dateType": "DC_Validated",
        "searchType": "Application",
    }
    
    # Create a session to manage cookies
    cookie_jar = load_cookies(COOKIE_FILE)
    session = requests.Session()
    session.cookies = cookie_jar
    
    response = None  # Initialize response variable
    for attempt in range(RETRY_COUNT):
        try:
            # Perform the POST request
            response = session.post(url, headers=headers, data=payload)
            
            # Check if the request was successful
            if response.ok:
                break  # Exit the loop on success
            else:
                print(f"HTTP error: {response.status_code}. Retrying {attempt + 1}/{RETRY_COUNT}...")
                time.sleep(RETRY_DELAY)  # Wait before retrying
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"Connection error: {e}. Retrying {attempt + 1}/{RETRY_COUNT}...")
            time.sleep(RETRY_DELAY)  # Wait before retrying

    # Check if the response is None, meaning all attempts failed
    if response is None or not response.ok:
        raise RuntimeError(f"Failed to fetch {url} after {RETRY_COUNT} attempts.")

    # Save cookies after the request
    save_cookies(cookie_jar, COOKIE_FILE)

    # Check for a successful request
    if response.status_code == 200:
        return response.text  # Return the HTML content of the page
    else:
        raise Exception(f"Failed to fetch the first page. Status code: {response.status_code}")

def parse_page(page_content):
    """
    Parse the HTML page content to extract the next page number and list of records.
    """
    # Extract the next page number
    next_page_match = re.search(r'searchCriteria.page=([\d]+)" class="next"', page_content)
    next_page_number = int(next_page_match.group(1)) if next_page_match else None

    # Extract list of records
    record_matches = re.findall(r'<li class="searchresult">.*?</li>', page_content, re.DOTALL)
    records = []
    for record in record_matches:
        # Extract keyVal
        key_val_match = re.search(r'keyVal=([^&]+)&', record)
        key_val = key_val_match.group(1) if key_val_match else None

        # Extract address
        address_match = re.search(r'<p class="address">.*?([\w\s,]+).*?</p>', record, re.DOTALL)
        address = address_match.group(1).strip() if address_match else None

        if key_val and address:
            records.append({'keyVal': key_val, 'address': address})

    return next_page_number, records

def get_next_page(next_page_number):
    """
    Fetch the content of the specified next page.
    """
    url = f"https://www.planning2.cityoflondon.gov.uk/online-applications/pagedSearchResults.do?action=page&searchCriteria.page={next_page_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.planning2.cityoflondon.gov.uk/online-applications/simpleSearchResults.do?action=firstPage",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }

    # Create a session to manage cookies
    cookie_jar = load_cookies(COOKIE_FILE)
    session = requests.Session()
    session.cookies = cookie_jar

    response = None  # Initialize response variable
    for attempt in range(RETRY_COUNT):
        try:
            # Perform the GET request
            response = session.get(url, headers=headers)
            
            # Check if the request was successful
            if response.ok:
                break  # Exit the loop on success
            else:
                print(f"HTTP error: {response.status_code}. Retrying {attempt + 1}/{RETRY_COUNT}...")
                time.sleep(RETRY_DELAY)  # Wait before retrying
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"Connection error: {e}. Retrying {attempt + 1}/{RETRY_COUNT}...")
            time.sleep(RETRY_DELAY)  # Wait before retrying

    # Check if the response is None, meaning all attempts failed
    if response is None or not response.ok:
        raise RuntimeError(f"Failed to fetch {url} after {RETRY_COUNT} attempts.")

    # Save cookies after the request
    save_cookies(cookie_jar, COOKIE_FILE)

    # Check for a successful request
    if response.status_code == 200:
        return response.text  # Return the HTML content of the page
    else:
        raise Exception(f"Failed to fetch page {next_page_number}. Status code: {response.status_code}")

def get_contact_details(keyVal):
    """
    Fetch and parse the contact details for the given keyVal.
    """
    url = f"https://www.planning2.cityoflondon.gov.uk/online-applications/applicationDetails.do?activeTab=contacts&keyVal={keyVal}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"https://www.planning2.cityoflondon.gov.uk/online-applications/applicationDetails.do?activeTab=details&keyVal={keyVal}",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }
    
    session = requests.Session()

    response = None  # Initialize response variable
    for attempt in range(RETRY_COUNT):
        try:
            # Fetch the contact details page
            response = session.get(url, headers=headers)
            
            # Check if the request was successful
            if response.ok:
                break  # Exit the loop on success
            else:
                print(f"HTTP error: {response.status_code}. Retrying {attempt + 1}/{RETRY_COUNT}...")
                time.sleep(RETRY_DELAY)  # Wait before retrying
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"Connection error: {e}. Retrying {attempt + 1}/{RETRY_COUNT}...")
            time.sleep(RETRY_DELAY)  # Wait before retrying

    # Check if the response is None, meaning all attempts failed
    if response is None or not response.ok:
        raise RuntimeError(f"Failed to fetch {url} after {RETRY_COUNT} attempts.")

    if response.status_code != 200:
        print(f"Failed to fetch contact details for keyVal: {keyVal}. Status code: {response.status_code}")
        return {'name': None, 'email': None}

    # Parse the HTML content for name and email
    page_content = response.text
    contact_match = re.search(
        r'<div class="agents">.*?<p>(.*?)</p>.*?<th scope="row">.*?Email.*?</th>\s*<td>(.*?)</td>.*?</div>',
        page_content,
        re.DOTALL | re.IGNORECASE,
    )

    name = contact_match.group(1).strip() if contact_match else None
    email = contact_match.group(2).strip() if contact_match else None
    
    if name:
        name = re.sub(r'^\b(Mr|Mrs|Ms|Miss|Dr)\b\.?\s*', '', name, flags=re.IGNORECASE)

    return {'name': name, 'email': email}

def save_line(address, name, email):
    """
    Append a row with address, name, and email to the in-memory CSV.
    """
    # Check if email is valid (not empty and does not end with '.gov')
    if email and not email.endswith(".gov") and "tree" not in email.lower():
        # In-memory CSV handling
        writer = csv.writer(CSV_MEMORY)
        writer.writerow([address, name, email])

def get_month_list(start_month=None, end_month=None):
    """
    Returns a list of months in "Mon YY" format
    """
    now = datetime.now()

    # Determine the start month
    start_month = start_month or START_MONTH
    if start_month:
        start_date = datetime.strptime(start_month, "%b %y")
    else:
        # Default to last month
        start_date = now.replace(day=1) - timedelta(days=1)
        start_date = start_date.replace(day=1)

    # Determine the end month
    end_month = end_month or END_MONTH
    if end_month:
        end_date = datetime.strptime(end_month, "%b %y")
    else:
        # Default to current month
        end_date = now.replace(day=1)

    # Swap months if the range is reversed
    if (start_date > end_date):
        start_date, end_date = end_date, start_date

    # Generate months
    months = []
    while start_date <= end_date:
        months.append(start_date.strftime("%b %y"))
        start_date += timedelta(days=32)  # Move to the next month
        start_date = start_date.replace(day=1)  # Reset to the first day of the month

    return months[::DIRECTION]  # Return the list ordered based on DIRECTION

def get_ward_list():
    """
    Fetches the list of wards from the given URL
    """
    url = 'https://www.planning2.cityoflondon.gov.uk/online-applications/search.do?action=monthlyList'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.planning2.cityoflondon.gov.uk/online-applications/search.do?action=weeklyList',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Load cookies from the file
    cookie_jar = load_cookies(COOKIE_FILE)
    session = requests.Session()
    session.cookies = cookie_jar

    # Retry logic for fetching the page
    for attempt in range(RETRY_COUNT):
        try:
            response = session.get(url, headers=headers)
            response.raise_for_status()  # Raise exception for HTTP errors
            break
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"Connection error: {e}. Retrying {attempt + 1}/{RETRY_COUNT}...")
            time.sleep(RETRY_DELAY)
        except requests.HTTPError as e:
            print(f"HTTP error: {e}. Cannot continue.")
            return []
    else:
        print("Failed to fetch the ward list after multiple attempts.")
        return []

    # Save cookies after the request
    save_cookies(cookie_jar, COOKIE_FILE)
    
    # Parse the page content and extract the <select> tag with id="ward"
    page_content = response.text
    ward_select_match = re.search(r'<select[^>]+id="ward"[^>]*>(.*?)</select>', page_content, re.DOTALL | re.IGNORECASE)
    
    if not ward_select_match:
        print('No <select> tag with id="ward" found.')
        return []

    # Extract options within the <select id="ward">
    ward_options = ward_select_match.group(1)
    ward_matches = re.findall(r'<option value="([^"]*)">([^<]*)</option>', ward_options, re.IGNORECASE)

    # Process the matches into a list of dictionaries
    ward_list = [{'value': value, 'name': name.strip()} for value, name in ward_matches if value]

    return ward_list

def scrape_data(start_month=None, end_month=None, selected_wards=None):
    """
    Main function to scrape data and return results.
    Returns both a list of data and CSV formatted data.
    """
    try:
        global CSV_MEMORY
        CSV_MEMORY = StringIO()  # Reset the in-memory CSV
        
        all_results = []
        
        # Init CSV header
        writer = csv.writer(CSV_MEMORY)
        writer.writerow(["Address", "Name", "Email"])
        
        csrf_token = get_search_page()  # Get CSRF token first
        month_list = get_month_list(start_month, end_month)
        
        # Get all wards or filter by selected wards
        all_wards = get_ward_list()
        if selected_wards:
            wards = [ward for ward in all_wards if ward['value'] in selected_wards]
        else:
            wards = all_wards
            
        # Limit the scope to prevent timeouts in serverless functions
        if len(month_list) > 2:
            month_list = month_list[:2]
        if len(wards) > 3:
            wards = wards[:3]
            
        for search_month_keyword in month_list:
            for ward in wards:
                first_page_content = get_first_page(csrf_token, search_month_keyword, ward['value'])
                next_page, records = parse_page(first_page_content)
                
                # Process first page records
                for record in records:
                    time.sleep(DELAY)
                    contact_details = get_contact_details(record['keyVal'])
                    
                    # Only include valid data
                    if contact_details['email'] and not contact_details['email'].endswith(".gov") and "tree" not in contact_details['email'].lower():
                        result = {
                            'address': record['address'],
                            'name': contact_details['name'],
                            'email': contact_details['email']
                        }
                        all_results.append(result)
                        save_line(record['address'], contact_details['name'], contact_details['email'])

                # Process additional pages if they exist
                while next_page is not None:
                    next_page_content = get_next_page(next_page)            
                    next_page, records = parse_page(next_page_content)
                    
                    for record in records:
                        time.sleep(DELAY)
                        contact_details = get_contact_details(record['keyVal'])
                        
                        # Only include valid data
                        if contact_details['email'] and not contact_details['email'].endswith(".gov") and "tree" not in contact_details['email'].lower():
                            result = {
                                'address': record['address'],
                                'name': contact_details['name'],
                                'email': contact_details['email']
                            }
                            all_results.append(result)
                            save_line(record['address'], contact_details['name'], contact_details['email'])
        
        # Get the CSV data as string
        csv_data = CSV_MEMORY.getvalue()
        
        return {
            'data': all_results,
            'csv': csv_data,
            'count': len(all_results),
            'months': month_list,
            'wards': [w['name'] for w in wards]
        }
                
    except Exception as e:
        print(f"Error in scraping: {e}")
        return {
            'error': str(e),
            'data': [],
            'csv': '',
            'count': 0,
            'months': [],
            'wards': []
        }

def main():
    # This function is kept for backward compatibility
    # For the API version, use scrape_data() function
    results = scrape_data()
    
    # If you want to save results to a local file when running as a script
    if results['count'] > 0:
        with open("cityoflondon_data.csv", "w", newline='', encoding='utf-8') as f:
            f.write(results['csv'])
        print(f"Scraping completed successfully with {results['count']} records")
    else:
        print("Scraping completed with no results or with errors")

if __name__ == "__main__":
    main()

    
    
