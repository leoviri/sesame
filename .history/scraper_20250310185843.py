import requests
import http.cookiejar
import re
import csv
import time
from datetime import datetime, timedelta

# Define the CSV file name as a global variable
CSV_FILE_NAME = "C:\Sesame\scraper_www.planning2.cityoflondon.gov.uk\cityoflondon.csv"

# Delay between fetching pages
DELAY = 30

# Retry configuration
RETRY_COUNT = 50  # Number of retries
RETRY_DELAY = 100  # Delay between retries (seconds)

# Define START_MONTH
# None for Default to last month
START_MONTH = "Jan 25"  # Example: "Jan 24"

# Define END_MONTH
# None for Default to the current month
END_MONTH = None  # Example: "Mar 24"

# For scraping in an ascending order
DIRECTION = -1
# For scraping in a descending order
# DIRECTION = -1


# File to store cookies
COOKIE_FILE = "cookies.txt"

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
    cookie_jar.save(cookie_file, ignore_discard=True, ignore_expires=True)

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
                #print(response.text)
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
    
    #print(payload)
    
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

    Args:
        page_content (str): HTML content of the page.

    Returns:
        tuple: A tuple containing:
            - next_page_number (int or None): The number of the next page if available, otherwise None.
            - records (list): A list of dictionaries with keys 'keyVal' and 'address'.
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

    Args:
        next_page_number (int): The page number to retrieve.

    Returns:
        str: The HTML content of the specified page.
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

    Args:
        keyVal (str): The unique key value of the application.

    Returns:
        dict: A dictionary containing 'name' and 'email', or None if not found.
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
        #print(name)
        name = re.sub(r'^\b(Mr|Mrs|Ms|Miss|Dr)\b\.?\s*', '', name, flags=re.IGNORECASE)

    return {'name': name, 'email': email}

def save_line(address, name, email):
    """
    Append a row with address, name, and email to the specified CSV file.

    Args:
        address (str): The address value.
        name (str): The name value.
        email (str): The email value.
    """
    # Check if email is valid (not empty and does not end with '.gov')
    if email and not email.endswith(".gov") and "tree" not in email.lower():
        with open(CSV_FILE_NAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([address, name, email])  # Write as a single row

def get_month_list(start_month=None, end_month=None):
    """
    Returns a list of months in "Mon YY" format, either for the last month and current month
    or from the specified start month to the end month, in the order defined by DIRECTION.

    Args:
        start_month (str, optional): The starting month in "Mon YY" format (e.g., "Jan 23").
        end_month (str, optional): The ending month in "Mon YY" format (e.g., "Mar 23").

    Returns:
        list: List of months in "Mon YY" format, ordered based on DIRECTION.
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
    Fetches the list of wards from the given URL, parsing the <select> tag with id="ward" 
    and extracting the values and names of <option> elements.

    Returns:
        list: A list of dictionaries containing ward 'value' and 'name'.
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



def main():
    try:
        csrf_token = get_search_page()  # Get CSRF token first
        save_line("Address","Name","Email")
        month_list = get_month_list()
        ward_list = get_ward_list()
        current_month = 1
        for search_month_keyword in get_month_list():
            current_ward = 1
            for ward in ward_list:
                current_page = 1
                first_page_content = get_first_page(csrf_token, search_month_keyword, ward['value'])
                next_page, records = parse_page(first_page_content)
                print(f"Searching month: {search_month_keyword}")
                print(f"Searching ward: {ward['name']}")
                print(f"Page: {current_page}, Records: {len(records)}")
                current_record = 1
                for record in records:
                    print(f"Status, Record: {current_record}/{len(records)}, Page: {current_page}, Ward: '{ward['name']}' {current_ward}/{len(ward_list)}, Month: '{search_month_keyword}' {current_month}/{len(month_list)}\r", end="", flush=True)
                    time.sleep(DELAY)
                    contact_details = get_contact_details(record['keyVal'])
                    print(" " * 80, end="\r", flush=True)  # Clears the line with spaces
                    print(contact_details)
                    print(f"Address: {record['address']}\n")
                    save_line(record['address'], contact_details['name'], contact_details['email'])
                    
                    current_record += 1

                while next_page is not None:
                    current_page += 1
                    next_page_content = get_next_page(next_page)            
                    next_page, records = parse_page(next_page_content)
                    print(f"Page: {current_page}, Records: {len(records)}")
                    for record in records:
                        print(f"Status, Record: {current_record}/{len(records)}, Page: {current_page}, Ward: '{ward['name']}' {current_ward}/{len(ward_list)}, Month: '{search_month_keyword}' {current_month}/{len(month_list)}\r", end="", flush=True)
                        time.sleep(DELAY)
                        contact_details = get_contact_details(record['keyVal'])
                        print(" " * 80, end="\r", flush=True)  # Clears the line with spaces
                        print(contact_details)
                        print(f"Address: {record['address']}\n")
                        save_line(record['address'], contact_details['name'], contact_details['email'])
                
                        current_record += 1
                    #current_page += 1
                current_ward += 1
            current_month += 1
                
    except Exception as e:
        print(e)
        
    print("Scraping completed successfully")

if __name__ == "__main__":
    main()

    
    
