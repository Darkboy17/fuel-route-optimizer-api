"""
This script reads the fuel price CSV file, extracts unique city/state pairs,
and uses the Nominatim API to geocode them into coordinates ( because coordinates are missing in the CSV which is required for the map). It caches successful geocodes in a JSON file and logs failures separately. The reason for this script is to avoid making repeated API calls for the same locations, which can lead to hitting rate limits and unnecessary delays. By caching results, you can run this script once to populate the cache and then use the cached coordinates in your main application without worrying about API limits.

Usage:
    python geocode_csv.py
    
Notes:
    This script does not require an API key for the Nominatim API.
    The CSV file should be in the /data folder under the root directory as this script.
    The script respects Nominatim's usage policy by including a User-Agent header and adding a delay between requests.
    Caching results allows you to run the script multiple times without re-querying the API for already processed locations.
    Failed geocodes are logged with error messages for troubleshooting.  
"""

from pathlib import Path
import requests
import csv
import json
import time

CSV_FILE = Path("data/fuel-prices-for-be-assessment.csv")
CACHE_FILE = Path("data/city_cache.json")
FAILED_FILE = Path("data/failed_city_geocodes.json")

# Delay between API requests in seconds to respect Nominatim's usage policy and avoid hitting rate limits
REQUEST_DELAY_SECONDS = 1


def make_city_key(city, state):
    """Creates a standardized key for caching and lookup."""
    
    # Standardize the city and state by stripping whitespace and converting to uppercase
    city = city.strip().upper()
    state = state.strip().upper()
    
    return f"{city},{state}"


def geocode_city(city, state):
    """
    Geocodes a city/state pair using the Nominatim API and returns coordinates as [longitude, latitude].
    Returns None if no results are found.
    Raises requests.RequestException for network-related errors.
    """
    
    # Nominatim API endpoint for searching locations
    url = "https://nominatim.openstreetmap.org/search"

    # Parameters for the API request
    params = {
        "city": city,
        "state": state,
        "country": "USA",
        "format": "json",
        "limit": 1,
    }

    # Nominatim requires a User-Agent header to identify the application making requests
    headers = {
        "User-Agent": "fuel-route-app/1.0"
    }

    # Make the API request with a timeout to prevent hanging indefinitely
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20,
    )

    # Raise an exception for HTTP errors (e.g., 4xx or 5xx responses)
    response.raise_for_status()
    
    # Parse the JSON response to extract coordinates
    data = response.json()

    if not data:
        return None

    return [
        float(data[0]["lon"]),
        float(data[0]["lat"]),
    ]


def load_json_file(path):
    """
    Loads a JSON file and returns its contents as a dictionary. Returns an empty dictionary if the file does not exist.
    """
    
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_file(path, data):
    """
    Saves a dictionary to a JSON file with pretty formatting.
    Creates the file if it doesn't exist.
    """
    
    # Open the file in write mode to overwrite existing content or create a new file if it doesn't exist
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def collect_unique_city_states():
    """
    Reads the CSV file and collects unique city/state pairs, returning a dictionary keyed by a standardized city/state key.
    The values are dictionaries containing the original city and state for display purposes.
    Returns:
        dict: A dictionary of unique city/state pairs keyed by a standardized key.
    """
    
    # Use a dictionary to store unique city/state pairs, keyed by a standardized key for easy lookup and caching
    unique_locations = {}

    # Open the CSV file and read it using DictReader to access columns by name
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        # Iterate through each row in the CSV and extract city and state information
        for row in reader:
            city = row["City"].strip()
            state = row["State"].strip()

            if not city or not state:
                continue

            key = make_city_key(city, state)

            # Store clean display values for the API call
            unique_locations[key] = {
                "city": city.title(),
                "state": state.upper(),
            }

    return unique_locations


def main():
    """
    Main function to orchestrate the geocoding process. It loads existing cache and failed results, collects unique city/state pairs from the CSV, and processes each pair by checking the cache and making API calls as needed. Results are saved back to the cache and failed files accordingly.
    """
    
    cache = load_json_file(CACHE_FILE)
    failed = load_json_file(FAILED_FILE)

    unique_locations = collect_unique_city_states()

    print("Unique city/state pairs:", len(unique_locations))
    print("Already cached:", len(cache))
    print("Already failed:", len(failed))

    # Process each unique city/state pair, skipping those already in the cache or failed lists
    for key, location in unique_locations.items():
        if key in cache or key in failed:
            continue

        city = location["city"]
        state = location["state"]

        print("Geocoding:", key)

        try:
            coordinates = geocode_city(city, state)

            if coordinates:
                cache[key] = coordinates
                save_json_file(CACHE_FILE, cache)
            else:
                failed[key] = "No result"
                save_json_file(FAILED_FILE, failed)

        except requests.RequestException as error:
            failed[key] = str(error)
            save_json_file(FAILED_FILE, failed)

        time.sleep(REQUEST_DELAY_SECONDS)

    print("Done.")
    print("Final cached:", len(cache))
    print("Final failed:", len(failed))


# Entry point for the script. When run directly, it will execute the main function to perform the geocoding process.
if __name__ == "__main__":
    main()