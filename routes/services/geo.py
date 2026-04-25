"""
Service for geospatial calculations, such as distance between two points on the Earth's surface.
"""

from math import radians, sin, cos, sqrt, atan2

# Average radius of the Earth in miles
EARTH_RADIUS_MILES = 3958.8

def haversine_miles(point_a, point_b):
    """
    Calculate the great circle distance in miles between two points on the Earth's surface using the Haversine formula.

    Args:
        point_a (tuple): A tuple containing the longitude and latitude of the first point (lon, lat).
        point_b (tuple): A tuple containing the longitude and latitude of the second point (lon, lat).

    Returns:
        float: The great circle distance in miles between the two points.
    """
    
    lon1, lat1 = point_a
    lon2, lat2 = point_b

    # Convert latitude and longitude from degrees to radians
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    # Calculate the differences in latitude and longitude
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula to calculate the distance between two points on the Earth's surface in miles
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    
    # Calculate the great circle distance in miles
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_MILES * c
