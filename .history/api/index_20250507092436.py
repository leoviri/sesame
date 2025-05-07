from http.server import BaseHTTPRequestHandler
import requests
import http.cookiejar
import re
import csv
import time
import json
import os
from datetime import datetime, timedelta
from io import StringIO
import concurrent.futures

# Define the storage location (temporary for Vercel functions)
COOKIE_CONTENT = ""

# Delay between fetching pages
DELAY = 5  # Reduced for API usage

# Retry configuration
RETRY_COUNT = 3  # Reduced for API usage
RETRY_DELAY = 10  # Reduced for API usage

# Direction 
DIRECTION = -1  # For scraping in a descending order

def load_cookies():
    """Load cookies from memory."""
    global COOKIE_CONTENT
    cookie_jar = http.cookiejar.LWPCookieJar()
    if COOKIE_CONTENT:
        try:
            temp_file = "/tmp/cookies.txt"
            with open(temp_file, "w") as f:
                f.write(COOKIE_CONTENT)
            cookie_jar.load(temp_file, ignore_discard=True, ignore_expires=True)
            os.remove(temp_file)
        except Exception as e:
            print(f"Cookie loading error: {e}")
    return cookie_jar

def save_cookies(cookie_jar):
    """Save cookies to memory."""
    global COOKIE_CONTENT
    temp_file = "/tmp/cookies.txt"
    try:
        cookie_jar.save(temp_file, ignore_discard=True, ignore_expires=True)
        with open(temp_file, "r") as f:
            COOKIE_CONTENT = f.read()
        os.remove(temp_file)
    except Exception as e:
        print(f"Cookie saving error: {e}")

def get_search_page():
    url = "https://www.planning2.cityoflondon.gov.uk/online-applications/search.do?action=simple&searchType=Application"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }
    
    # Load cookies and create a session
    cookie_jar = load_cookies()
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
    save_cookies(cookie_jar)

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
    cookie_jar = load_cookies()
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
    save_cookies(cookie_jar)

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
    cookie_jar = load_cookies()
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
    save_cookies(cookie_jar)

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

def get_month_list(start_month=None, end_month=None):
    """
    Returns a list of months in "Mon YY" format
    """
    now = datetime.now()
    
    # Default to last month if no start month is provided
    if not start_month:
        start_date = now.replace(day=1) - timedelta(days=1)
        start_date = start_date.replace(day=1)
    else:
        start_date = datetime.strptime(start_month, "%b %y")

    # Default to current month if no end month is provided
    if not end_month:
        end_date = now.replace(day=1)
    else:
        end_date = datetime.strptime(end_month, "%b %y")

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

    # Load cookies from memory
    cookie_jar = load_cookies()
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
    save_cookies(cookie_jar)
    
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

def scrape_month_ward(month, ward):
    """Scrape data for a specific month and ward"""
    results = []
    try:
        csrf_token = get_search_page()
        
        # Get first page
        first_page_content = get_first_page(csrf_token, month, ward['value'])
        next_page, records = parse_page(first_page_content)
        
        # Process first page records
        for record in records:
            time.sleep(DELAY)
            contact_details = get_contact_details(record['keyVal'])
            
            # Only include valid data (not empty and not ending with .gov)
            if contact_details['email'] and not contact_details['email'].endswith(".gov") and "tree" not in contact_details['email'].lower():
                results.append({
                    'address': record['address'],
                    'name': contact_details['name'], 
                    'email': contact_details['email']
                })
        
        # Process additional pages if they exist
        current_page = 1
        while next_page is not None:
            current_page += 1
            next_page_content = get_next_page(next_page)            
            next_page, records = parse_page(next_page_content)
            
            for record in records:
                time.sleep(DELAY)
                contact_details = get_contact_details(record['keyVal'])
                
                # Only include valid data
                if contact_details['email'] and not contact_details['email'].endswith(".gov") and "tree" not in contact_details['email'].lower():
                    results.append({
                        'address': record['address'],
                        'name': contact_details['name'], 
                        'email': contact_details['email']
                    })
    
    except Exception as e:
        print(f"Error scraping {month} - {ward['name']}: {str(e)}")
    
    return results

def generate_csv(data):
    """Generate CSV from the data"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Address", "Name", "Email"])
    for item in data:
        writer.writerow([item['address'], item['name'], item['email']])
    return output.getvalue()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - provide API information"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "message": "City of London Planning Scraper API",
            "endpoints": {
                "/api": "GET - This information",
                "/api/wards": "GET - List all wards",
                "/api/months": "GET - List available months",
                "/api/scrape": "POST - Run scraper with specific parameters"
            },
            "usage": "Send a POST request to /api/scrape with start_month, end_month and/or selected_wards parameters"
        }
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests - run the scraper"""
        if self.path == '/api/scrape':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                start_month = data.get('start_month')
                end_month = data.get('end_month')
                selected_wards = data.get('selected_wards', [])
                
                # Get months to scrape
                months = get_month_list(start_month, end_month)
                
                # Get all wards or use selected ones
                all_wards = get_ward_list()
                wards = [ward for ward in all_wards if not selected_wards or ward['value'] in selected_wards]
                
                if not wards:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"error": "No valid wards selected"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Use limited number of months and wards for API call to prevent timeouts
                if len(months) > 2:
                    months = months[:2]
                if len(wards) > 3:
                    wards = wards[:3]
                
                # Collect data
                all_results = []
                
                # Sequential processing for API version
                for month in months:
                    for ward in wards:
                        results = scrape_month_ward(month, ward)
                        all_results.extend(results)
                
                # Generate response based on requested format
                format_type = data.get('format', 'json')
                
                if format_type == 'csv':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/csv')
                    self.send_header('Content-Disposition', 'attachment; filename="cityoflondon_data.csv"')
                    self.end_headers()
                    csv_data = generate_csv(all_results)
                    self.wfile.write(csv_data.encode())
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "data": all_results,
                        "count": len(all_results),
                        "months": months,
                        "wards": [w['name'] for w in wards]
                    }
                    self.wfile.write(json.dumps(response).encode())
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
                
        elif self.path == '/api/wards':
            try:
                wards = get_ward_list()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(wards).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
                
        elif self.path == '/api/months':
            try:
                # Get available months (past year)
                now = datetime.now()
                months = []
                for i in range(12, -1, -1):  # Past year
                    date = now.replace(day=1) - timedelta(days=i*30)
                    months.append(date.strftime("%b %y"))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(months).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
                
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Endpoint not found"}
            self.wfile.write(json.dumps(response).encode()) 