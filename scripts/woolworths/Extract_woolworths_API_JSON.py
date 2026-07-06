import requests
import json
import os
import csv

# This API endpoint was manually discovered by inspecting network sources on webpage refreshes-
# while on the https://www.woolworths.co.nz/store-finder/search webpage.
# It provides a JSON output of Woolworths (formerly Countdown) store locations.
WOOLWORTHS_API_BASE_URL = "https://api.cdx.nz/site-location/api/v1/sites"
DEFAULT_LATITUDE = -41.24564052749397
DEFAULT_LONGITUDE = 173.1994906580824
# DEFAULT_MAX_RESULTS = 20 # Needs to be hidden to get all stores
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "woolworths_stores_API.json")
CSV_FILE = os.path.join(DATA_DIR, "woolworths_stores.csv")

def clean_null(value):
    """Clean null or empty values to return a default string."""
    if value is None:
        return ""
    if isinstance(value, str) and value.strip() == "":
        return ""
    return str(value)

def fetch_and_save_woolworths_stores():
    """Fetches store data from API URL and saves JSON and structured data into CSV."""
    headers = {
        ## Do not unhide the formatting - dosent give an output
        # "accept": "application/json, text/plain, */*",
        # "accept-encoding": "gzip, deflate, br, zstd",
        # "accept-language": "en-GB,en;q=0.9",
        # "origin": "https://www.woolworths.co.nz",
        # "priority": "u=1, i",
        # "referer": "https://www.woolworths.co.nz/",
        "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    
    params = {
        "latitude": DEFAULT_LATITUDE,
        "longitude": DEFAULT_LONGITUDE,
        # "maxResults": DEFAULT_MAX_RESULTS
    }

    print(f"Fetching data from: {WOOLWORTHS_API_BASE_URL} with parameters {params}")
    try:
        response = requests.get(WOOLWORTHS_API_BASE_URL, headers=headers, params=params, timeout=20)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        # Get the JSON data
        stores_data = response.json()

        # Ensure the data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

        # save the JSON data
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(stores_data, f, indent=4, ensure_ascii=False)
        print(f"Successfully downloaded and saved store JSON data to {OUTPUT_FILE}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    

    if response:
        # Parse the API response and save as CSV.
        sites = stores_data.get('siteDetail', [])
        if not sites:
            print("No site data found in the response.")
            return

        # Prepare data for our table
        table_data = []
        for item in sites:
            site = item.get('site', {})
            
            # Extract basic details
            name = clean_null(site.get('name'))
            suburb = clean_null(site.get('suburb'))
            address = clean_null(site.get('addressLine1'))
            postcode = clean_null(site.get('postcode'))
            state = clean_null(site.get('state'))
            distance = f"{item.get('distanceInKms', 'N/A')} km"
            # Extract facilities
            facilities = site.get('facilityList', {}).get('facility', [])
            facilities_str = ", ".join(facilities) if facilities else "None listed"
            # Extract representative trading hours (e.g., Monday from the first available week)
            # trading_hours_list = item.get('tradingHours', [])
            # hours_str = "N/A"
            # if trading_hours_list:
            #     week_data = trading_hours_list[0]
            #     monday = week_data.get('monday', {})
            #     if monday:
            #         start = monday.get('startTime', '?')
            #         end = monday.get('endTime', '?')
            #         hours_str = f"Mon: {start} - {end}"
            # Append as a row
            table_data.append([
                name,
                suburb,
                address,
                postcode,
                state,
                # hours_str,
                distance,
                facilities_str
            ])
            # Define table headers

        headers = [
            "Store Name", 
            "Suburb", 
            "Address", 
            "Postcode", 
            "State", 
            # "Representative Hours",
            "Distance", 
            "Key Facilities"
        ]

        # Write to CSV
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(table_data)
            print(f"Successfully saved structured data for {len(sites)} woolworths stores at {OUTPUT_FILE}.\n")



if __name__ == "__main__":
    fetch_and_save_woolworths_stores()