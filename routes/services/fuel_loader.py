"""
Service to load fuel station data from a CSV file and cache city coordinates for efficient retrieval.
"""
import csv
import json
from pathlib import Path
from functools import lru_cache
from .utils import make_city_key

# Constants
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CSV_PATH = BASE_DIR / "data" / "fuel-prices-for-be-assessment.csv"


@lru_cache(maxsize=1)
def load_fuel_stations():
    """Load fuel station data from a CSV file and cache city coordinates for efficient retrieval.
    Returns:
        list: A list of dictionaries, each representing a fuel station with its details and coordinates.
    """
    
    stations = []

    # Load cached city coordinates
    with open("data/city_cache.json", "r", encoding="utf-8") as file:
        cache = json.load(file)

    # Read fuel station data from given CSV
    with open("data/fuel-prices-for-be-assessment.csv", newline="", encoding="utf-8-sig") as file:
        
        # Use DictReader to read CSV into a list of dictionaries
        reader = csv.DictReader(file)

        # Iterate through each row in the CSV and extract relevant information
        for row in reader:
            
            # Create a unique key for the city and state to look up coordinates in the cache
            key = make_city_key(row["City"], row["State"])
            
            # Retrieve coordinates from the cache using the generated key
            coordinates = cache.get(key)

            # If coordinates are not found in the cache, skip this station
            if not coordinates:
                continue
            
            # Append the station information to the list of stations
            stations.append({
                "id": row["OPIS Truckstop ID"],
                "name": row["Truckstop Name"],
                "city": row["City"],
                "address": row["Address"],
                "state": row["State"],
                "price": float(row["Retail Price"]),
                "coordinates": coordinates,
            })

    return stations