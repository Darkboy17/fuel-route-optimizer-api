"""
Service for routing using OpenRouteService API. 
This module provides a function to get a route between two points, returning the geometry and distance in miles. 
It also includes error handling and debugging information for API responses.
"""

import json
import time
import requests
from django.conf import settings

# OpenRouteService API endpoint for driving directions in GeoJSON format
ORS_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
)


def get_route(start_coordinates, finish_coordinates):
    """Get a route between two points using OpenRouteService API.
    Args:
        start_coordinates (list): [longitude, latitude] of the starting point.
        finish_coordinates (list): [longitude, latitude] of the finishing point.
    Returns:
        dict: A dictionary containing the route geometry, distance in miles, and raw GeoJSON response.
    Raises:
        ValueError: If the API response is not successful or if no route is found.
    """
    
    # Prepare headers and payload for the API request
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Accept": "application/json, application/geo+json",
        "Content-Type": "application/json",
    }

    # The API expects coordinates in [longitude, latitude] format
    payload = {
        "coordinates": [
            start_coordinates,
            finish_coordinates,
        ]
    }
    
    # Measure the time taken for the API request
    ors_start_time = time.perf_counter()

    # Make the POST request to the OpenRouteService API
    response = requests.post(
        ORS_DIRECTIONS_URL,
        json=payload,
        headers=headers,
        timeout=20,
    )
    
    # Calculate elapsed time for the API request
    ors_elapsed_time = time.perf_counter() - ors_start_time
    
    # Debugging information about the API response
    print(f"OpenRouteService API time: {ors_elapsed_time:.3f} seconds")
    print(f"OpenRouteService status: {response.status_code}")

    # Parse the JSON response
    data = response.json()

    # Pretty print smaller useful parts
    # print("STATUS:", response.status_code)
    # print("TOP LEVEL KEYS:", data.keys())

    # Save full response to file
    with open("ors_response_debug.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    # Check if the API response is successful
    if response.status_code != 200:
        raise ValueError(data)

    # Extract the route geometry and distance from the response
    features = data.get("features", [])

    # If no features are found, raise an error with the full response for debugging
    if not features:
        raise ValueError(f"No route found. Full response saved to ors_response_debug.json")

    # Assuming we take the first feature as the route
    feature = features[0]

    return {
        "geometry": feature["geometry"]["coordinates"],
        "distance_miles": feature["properties"]["summary"]["distance"] / 1609.34,
        "raw_geojson": data,
    }