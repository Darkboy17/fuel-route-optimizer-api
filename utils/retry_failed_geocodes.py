"""
This script attempts to retry geocoding for cities that previously failed. It uses the Nominatim API first, and if that fails, it tries the Open-Meteo geocoding API. The script also includes some cleaning of city names to improve geocoding success. It saves progress after each attempt to ensure that we don't lose data if the script is interrupted. Additionally, it keeps track of how many entries were recovered, how many were already cached, and how many were removed for being non-US (if that logic is enabled). Finally, it outputs a summary of the results after processing all failed entries.
If there are entries in the failed list called "failed_city_geocodes.json" that are not in the cache, it will attempt to geocode them again and update the cache and failed lists accordingly. If an entry is successfully geocoded, it will be removed from the failed list and added to the cache. If it still fails after retrying, it will be moved to a new list called "still_failed_city_geocodes.json" for further review. Repeated runs of this script can help recover more geocodes over time as APIs improve and data gets cleaned up. IF there are still failed entries, it could possibly mean that they are non-US cities or have some other issue that prevents geocoding, so those would need to be reviewed manually. The script also includes a delay between requests to avoid hitting API rate limits.
"""

from pathlib import Path
import requests
import json
import time


CACHE_FILE = Path("data/city_cache.json")
FAILED_FILE = Path("data/failed_city_geocodes.json")
RETRY_FAILED_FILE = Path("data/still_failed_city_geocodes.json")

REQUEST_DELAY_SECONDS = 1

# List of US state abbreviations for basic validation (can be expanded if needed)
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}


def load_json(path):
    """Load JSON data from a file, returning an empty dict if the file doesn't exist.
    Args:
        path (Path): The path to the JSON file.
    Returns:
        dict: The loaded JSON data, or an empty dict if the file doesn't exist.
    """
    
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    """Save JSON data to a file with pretty formatting.
    Args:
        path (Path): The path to the JSON file.
        data (dict): The data to save.
    """
    
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def clean_city_for_geocoding(city):
    """Clean and standardize city names to improve geocoding success. This function applies common formatting and replacements to city names.
    Args:
        city (str): The city name to clean.
    Returns:
        str: The cleaned city name.
    """
    
    city = city.strip().title()

    # Common formatting replacements to improve geocoding success
    replacements = {
        "Mc ": "Mc",
        "De ": "De",
        "Du ": "Du",
        "La ": "La",
        "Saint ": "St ",
        "Oneill": "O'Neill",
        "Odonnell": "O'Donnell",
    }

    # Apply replacements to the city name
    for old, new in replacements.items():
        city = city.replace(old, new)

    return city


def geocode_with_nominatim(city, state):
    """
    Geocode a city and state using the Nominatim API. This function first tries a structured query with separate city and state parameters, and if that fails, it tries a single query string combining city and state. It includes a User-Agent header to avoid being blocked by the API and sets a timeout for the request."""
    
    # URL for Nominatim geocoding API
    url = "https://nominatim.openstreetmap.org/search"

    # List of possible query formats
    queries = [
        {
            "city": city,
            "state": state,
            "country": "USA",
            "format": "json",
            "limit": 1,
        },
        {
            "q": f"{city}, {state}, USA",
            "format": "json",
            "limit": 1,
        },
    ]

    # Nominatim requires a User-Agent header to identify the application making requests, so we will include that in our requests to avoid being blocked. We will also set a timeout to prevent hanging on slow responses.
    headers = {
        "User-Agent": "fuel-route-app/1.0"
    }

    # Try each query format until we get a successful geocode or exhaust all options
    for params in queries:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()

        data = response.json()

        if data:
            return [
                float(data[0]["lon"]),
                float(data[0]["lat"]),
            ]

    return None


def geocode_with_open_meteo(city, state):
    """
    Geocode a city and state using the Open-Meteo geocoding API. This function constructs a query with the city and state, and includes parameters to limit results to the US and return JSON format. It also sets a timeout for the request.
    Args:
        city (str): The city name to geocode.
        state (str): The state abbreviation to geocode.
    Returns:
        list: A list containing the longitude and latitude of the geocoded location, or None if no results are found.
    """
    
    # URL for Open-Meteo geocoding API
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # Construct query parameters to search for the city and state, limit results to the US, and return JSON format. We will also set a timeout to prevent hanging on slow responses.
    params = {
        "name": f"{city}, {state}",
        "count": 1,
        "language": "en",
        "format": "json",
        "countryCode": "US",
    }

    # Make the GET request to the Open-Meteo geocoding API with the specified parameters and timeout. We will also check for HTTP errors and raise an exception if the request fails.
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    # Parse the JSON response and extract the results.
    data = response.json()
    results = data.get("results", [])

    # If there are results, return the longitude and latitude of the first result as a list. 
    if not results:
        return None

    # Assign the first result to a variable for easier access and readability.
    result = results[0]

    return [
        float(result["longitude"]),
        float(result["latitude"]),
    ]


def retry_failed_geocodes():
    """Main function to retry geocoding for failed entries. This function loads the cache and failed lists, iterates through the failed entries, and attempts to geocode them again using the defined geocoding functions. It also includes logic to clean city names, check for already cached entries, and handle non-US entries if that logic is enabled. Progress is saved after each attempt to ensure data integrity, and a summary of results is printed at the end."""
    
    cache = load_json(CACHE_FILE)
    failed = load_json(FAILED_FILE)
    still_failed = {}

    recovered_count = 0
    removed_non_us_count = 0
    already_cached_count = 0

    print("Failed entries to review:", len(failed))

    # Iterate through the failed entries and attempt to geocode them again. We will also include logic to clean city names, check for already cached entries, and handle non-US entries if that logic is enabled. Progress will be saved after each attempt to ensure data integrity, and a summary of results will be printed at the end.
    for key in list(failed.keys()):
        try:
            city, state = key.split(",", 1)
        except ValueError:
            still_failed[key] = "Invalid key format"
            continue

        city = city.strip()
        state = state.strip().upper()

        # ✅ If already in cache, remove it from failed
        if key in cache:
            print("Already cached, removing from failed:", key)
            failed.pop(key, None)
            already_cached_count += 1
            continue

        # ✅ If non-US, remove it from failed because we don't need it
        # if state not in US_STATES:
        #     print("Non-US, removing from failed:", key)
        #     failed.pop(key, None)
        #     removed_non_us_count += 1
        #     continue

        clean_city = clean_city_for_geocoding(city)

        print("Retrying:", key, "->", clean_city, state)

        try:
            coordinates = geocode_with_nominatim(clean_city, state)

            if not coordinates:
                print("Nominatim failed, trying Open-Meteo:", key)
                coordinates = geocode_with_open_meteo(clean_city, state)

            if coordinates:
                cache[key] = coordinates
                failed.pop(key, None)
                recovered_count += 1
                print("Recovered:", key)
            else:
                still_failed[key] = "No result after retry"
                print("Still failed:", key)

        except requests.RequestException as error:
            still_failed[key] = str(error)
            print("Request error:", key, error)

        time.sleep(REQUEST_DELAY_SECONDS)

        # ✅ Save progress after every attempt
        save_json(CACHE_FILE, cache)
        save_json(FAILED_FILE, failed)
        save_json(RETRY_FAILED_FILE, still_failed)

    save_json(CACHE_FILE, cache)
    save_json(FAILED_FILE, failed)
    save_json(RETRY_FAILED_FILE, still_failed)

    print("Done.")
    print("Recovered now:", recovered_count)
    print("Already cached removed:", already_cached_count)
    print("Non-US removed:", removed_non_us_count)
    print("Remaining failed:", len(failed))
    print("Still failed after retry:", len(still_failed))


# If this script is run directly, execute the retry_failed_geocodes function to start the process of retrying geocoding for failed entries. This allows us to easily run this script as a standalone utility to recover more geocodes over time.
if __name__ == "__main__":
    retry_failed_geocodes()