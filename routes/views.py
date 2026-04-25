"""
This module defines the API view for calculating the optimal fuel stops along a route between two points in the USA. It handles POST requests with start and finish coordinates, validates the input, retrieves the route, finds nearby fuel stations, optimizes fuel stops, and calculates total fuel cost. The response includes the route distance, recommended fuel stops, total fuel cost, and a GeoJSON representation of the route for mapping purposes.
"""

# Create your views here.
from .services.fuel_loader import load_fuel_stations
from rest_framework.response import Response
from rest_framework.views import APIView
from .services.utils import is_in_usa_bbox, is_point_in_usa, is_valid_coordinate
from .services.routing import get_route
from django.shortcuts import render
from rest_framework import status
from .services.optimizer import (
    find_nearby_stations,
    choose_fuel_stops,
    calculate_total_fuel_cost,
)

class RouteFuelView(APIView):
    """API view to calculate optimal fuel stops along a route between two points in the USA.
    Expects POST requests with 'start' and 'finish' coordinates in the format [lon, lat].
    Validates input, retrieves route, finds nearby fuel stations, optimizes fuel stops, and calculates total fuel cost. Returns route distance, recommended fuel stops, total fuel cost, and a GeoJSON representation of the route.
    
    Example request body:
    {
        "start": [-122.4194, 37.7749],  # San Francisco (lon, lat)
        "finish": [-74.0060, 40.7128]    # New York City (lon, lat)
    }
    
    Returns:
        Response: A response containing the route distance, recommended fuel stops, total fuel cost, and a GeoJSON representation of the route. If the input is invalid or an error occurs, returns an appropriate error message and status code.
    """
    def post(self, request):
        """Handle POST requests to calculate optimal fuel stops along a route between two points in the USA."""
        
        # Extract start and finish coordinates from the request data
        start = request.data.get("start")
        finish = request.data.get("finish")
        

        # Check if start and finish coordinates are provided
        if not start or not finish:
            return Response(
                {"error": "Both start and finish coordinates are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        # Extract longitude and latitude from start and finish coordinates
        start_lon, start_lat = start
        finish_lon, finish_lat = finish

        # Validate that the provided coordinates are valid geographic coordinates and located within the USA
        if not is_valid_coordinate(start_lon, start_lat) or not is_valid_coordinate(finish_lon, finish_lat):
            return Response(
                {"error": "Invalid coordinate values."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate that both start and finish points are located within the USA using the is_point_in_usa function, which performs a fast bounding box check followed by a reverse geocoding API call to confirm the country code for the given coordinates. If either point is outside the USA, return an error response indicating that both points must be within the USA.
        if not is_point_in_usa(start_lat, start_lon) or not is_point_in_usa(finish_lat, finish_lon):
            return Response(
                {"error": "Both start and finish must be within the USA"},
                status=status.HTTP_400_BAD_REQUEST,
            )
                
        # Validate that start and finish are lists of two elements (lon, lat)
        if (
            not isinstance(start, list) or len(start) != 2 or
            not isinstance(finish, list) or len(finish) != 2
        ):
            return Response(
                {"error": "Start and finish must be [lon, lat] arrays"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        try:
            # Get the route between the start and finish coordinates
            route = get_route(start, finish)

            # Find nearby fuel stations along the route and optimize fuel stops
            stations = load_fuel_stations()
            nearby_stations = find_nearby_stations(
                route["geometry"],
                stations,
            )

            # Choose optimal fuel stops based on the route distance and nearby stations
            fuel_stops = choose_fuel_stops(
                route["distance_miles"],
                nearby_stations,
            )

            # Calculate the total fuel cost for the route based on the distance and chosen fuel stops
            total_cost = calculate_total_fuel_cost(
                route["distance_miles"],
                fuel_stops,
            )
            
            # Debugging output to verify the route distance, number of route points, total stations loaded, and nearby stations found
            print("Route distance:", route["distance_miles"])
            print("Route points:", len(route["geometry"]))

            # Load fuel stations and print the total number of stations loaded for debugging purposes
            stations = load_fuel_stations()
            print("Total stations:", len(stations))

            # Find nearby stations again and print the number of nearby stations found for debugging purposes
            nearby_stations = find_nearby_stations(route["geometry"], stations)
            print("Nearby stations:", len(nearby_stations))
            

            # Return the response containing the route distance, recommended fuel stops, total fuel cost, and a GeoJSON representation of the route for mapping purposes
            return Response({
                "distance_miles": round(route["distance_miles"], 2),
                "fuel_stops": fuel_stops,
                "total_fuel_cost": total_cost,
                "route_map": route["raw_geojson"],
            })

        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )