"""Utility/Helper functions for use in services."""

import requests

def is_in_usa_bbox(lat, lon):
    """Check if the given latitude and longitude are within the bounding box of the USA.
    This is a fast preliminary check to avoid unnecessary API calls for points that are clearly outside the USA.
    The bounding box covers the contiguous United States, excluding Alaska and Hawaii."""
    
    return (
        24.396308 <= lat <= 49.384358 and
        -125.0 <= lon <= -66.93457
    )
    

def is_valid_coordinate(lon, lat):
    """Check if the given longitude and latitude are valid geographic coordinates.
    Longitude must be between -180 and 180 degrees, and latitude must be between -90 and 90 degrees.
    """
    return -180 <= lon <= 180 and -90 <= lat <= 90


def is_point_in_usa(lat, lon):
    """
    Check if the given latitude and longitude are located within the United States using the Nominatim reverse geocoding API.
    This function first performs a fast bounding box check to quickly reject points that are clearly outside the USA, and then makes an API call to get the country code for the given coordinates. If the country code is "us", it returns True; otherwise, it returns False.
    """
    
    # Fast rejection first
    if not is_in_usa_bbox(lat, lon):
        return False

    url = "https://nominatim.openstreetmap.org/reverse"

    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 10,
    }

    headers = {
        "User-Agent": "fuel-route-app/1.0"
    }

    # Make the API call to get the country code for the given coordinates
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    country_code = data.get("address", {}).get("country_code")

    return country_code == "us"


def make_city_key(city, state):
    """
    Create a standardized city key in the format "CITY,STATE" for consistent lookups.
    This function takes a city name and state abbreviation, strips whitespace, converts to uppercase, and replaces common abbreviations like "ST" with "SAINT" and "FT" with "FORT" to create a standardized key for looking up fuel stations by city and state.
    Args:        
        city (str): The name of the city.
        state (str): The abbreviation of the state.
    Returns:
        str: A standardized city key in the format "CITY,STATE" for consistent lookups.
    """
    
    city = city.strip().upper().replace(".", "")
    state = state.strip().upper()
    city = city.replace("ST ", "SAINT ")
    city = city.replace("FT ", "FORT ")
    return f"{city},{state}"