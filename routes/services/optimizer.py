"""
Services for optimizing fuel stops along a route, including:
- Building a spatial grid of stations for efficient lookup
- Sampling route geometry to find nearby stations
- Choosing fuel stops based on route distance and station prices
- Calculating total fuel cost based on stops and route distance
"""

from collections import defaultdict
from .geo import haversine_miles

# This constant defines the maximum distance (in miles) a vehicle can travel on a full tank of fuel.
MAX_RANGE_MILES = 500

# This constant defines the miles per gallon for the vehicle, used to calculate fuel needs and costs.
MPG = 10

# This constant defines the buffer distance (in miles) around the route to consider stations as "nearby".
ROUTE_BUFFER_MILES = 25

# This constant defines the minimum distance (in miles) between two consecutive stops. 
# This helps ensure that we don't choose stations that are too close to each other, which could lead to inefficient stops.
MIN_PROGRESS_MILES = 400

# Roughly 1 degree latitude = 69 miles
MILES_PER_DEGREE = 69

# Grid size in degrees.
# 0.5 degrees ≈ 35 miles, good enough for 25-mile search buffer.
GRID_SIZE = 0.5


def get_grid_cell(coordinates):
    """Convert geographic coordinates (longitude, latitude) into a grid cell identifier based on a defined grid size.
    Args:
        coordinates (tuple): A tuple containing the longitude and latitude of a point (lon, lat).
    Returns:
        tuple: A tuple containing the latitude and longitude of the grid cell.
    """
    
    lon, lat = coordinates

    return (
        int(lat / GRID_SIZE),
        int(lon / GRID_SIZE),
    )


def build_station_grid(stations):
    """Build a spatial grid of stations based on their geographic coordinates.
    Args:
        stations (list): A list of dictionaries, each representing a fuel station with its details and coordinates.
    Returns:
        defaultdict: A dictionary with grid cell identifiers as keys and lists of stations in each cell as values.
    """

    # Create a grid mapping from cell identifiers to lists of stations in those cells.
    grid = defaultdict(list)

    # Iterate through each station and assign it to the appropriate grid cell based on its coordinates.
    for station in stations:
        coordinates = station.get("coordinates")

        if not coordinates:
            continue

        cell = get_grid_cell(coordinates)
        grid[cell].append(station)

    return grid


def get_neighboring_cells(cell):
    """Get the neighboring grid cells of a given cell.
    Args:
        cell (tuple): A tuple containing the latitude and longitude of a grid cell.
    Returns:
        list: A list of tuples representing the neighboring grid cells.
    """
    lat_cell, lon_cell = cell

    cells = []

    # Loop through the offsets to get the neighboring cells (including the original cell).
    for lat_offset in [-1, 0, 1]:
        for lon_offset in [-1, 0, 1]:
            cells.append(
                (lat_cell + lat_offset, lon_cell + lon_offset)
            )

    return cells


def sample_route_by_distance(route_geometry, interval_miles=5):
    """Sample points along the route geometry at regular distance intervals.
    Args:
        route_geometry (list): A list of tuples representing the longitude and latitude of points along the route.
        interval_miles (int, optional): The distance interval in miles at which to sample points along the route. Defaults to 5 miles.
    Returns:
        tuple: A tuple containing two lists: the sampled points and the corresponding distances in miles.
    """
    
    # Start with the first point of the route and initialize the total distance and next sample mile.
    sampled_points = [route_geometry[0]]
    sampled_miles = [0]

    # These variables will keep track of the total distance traveled along the route and the next mile marker at which to sample a point.
    total_miles = 0
    next_sample_mile = interval_miles

    # Iterate through the route geometry starting from the second point, calculating the distance between consecutive points and sampling points at regular intervals.
    for index in range(1, len(route_geometry)):
        
        # Get the previous point and the current point from the route geometry.
        previous_point = route_geometry[index - 1]
        current_point = route_geometry[index]

        # Calculate the distance in miles between the previous point and the current point using the Haversine formula, and add it to the total distance traveled along the route.
        total_miles += haversine_miles(previous_point, current_point)

        # If the total distance traveled has reached or exceeded the next sample mile, add the current point to the list of sampled points and update the next sample mile by adding the interval miles.
        if total_miles >= next_sample_mile:
            sampled_points.append(current_point)
            sampled_miles.append(total_miles)
            next_sample_mile += interval_miles

    # Ensure the last point of the route is included in the sampled points if it wasn't already added during the loop.
    if sampled_points[-1] != route_geometry[-1]:
        sampled_points.append(route_geometry[-1])
        sampled_miles.append(total_miles)

    return sampled_points, sampled_miles


def find_nearby_stations(route_geometry, stations):
    """Find fuel stations that are within a certain distance from the route geometry.
    Args:
        route_geometry (list): A list of tuples representing the longitude and latitude of points along the route.
        stations (list): A list of dictionaries, each representing a fuel station with its details and coordinates.
    Returns:
        dict: A dictionary with station IDs as keys and dictionaries of station details as values.
    """
    
    # This dictionary will store the nearby stations, using station IDs as keys to ensure uniqueness and to allow for easy updates if a closer station is found.
    nearby_stations = {}

    # Build a spatial grid of stations for efficient lookup based on their geographic coordinates.
    station_grid = build_station_grid(stations)

    # Sample points along the route geometry at regular distance intervals to reduce the number of distance calculations needed when finding nearby stations.
    route_points, route_miles = sample_route_by_distance(
        route_geometry,
        interval_miles=5,
    )

    # For each sampled point along the route, determine the grid cell it falls into and check the neighboring cells for stations. Calculate the distance from the route point to each station in those cells, and if the station is within the defined buffer distance, add it to the nearby stations dictionary. If a station is already in the dictionary but a closer route point is found, update the station's details with the closer distance and corresponding route mile.
    for index, route_point in enumerate(route_points):
        route_cell = get_grid_cell(route_point)
        nearby_cells = get_neighboring_cells(route_cell)

        for cell in nearby_cells:
            stations_in_cell = station_grid.get(cell, [])

            for station in stations_in_cell:
                station_id = station.get("id") or station["name"]
                station_coordinates = station["coordinates"]

                distance = haversine_miles(route_point, station_coordinates)

                if distance > ROUTE_BUFFER_MILES:
                    continue

                existing_station = nearby_stations.get(station_id)

                if (
                    existing_station is None
                    or distance < existing_station["distance_from_route"]
                ):
                    station_copy = station.copy()
                    station_copy["distance_from_route"] = round(distance, 2)
                    station_copy["route_mile"] = round(route_miles[index], 2)

                    nearby_stations[station_id] = station_copy

    return list(nearby_stations.values())


def choose_fuel_stops(route_distance_miles, nearby_stations):
    """Choose fuel stops along the route based on the total route distance and the nearby stations.
    Args:        
        route_distance_miles (float): The total distance of the route in miles.
        nearby_stations (list): A list of dictionaries, each representing a nearby fuel station with its details and distance from the route.
    Returns:        
        list: A list of dictionaries representing the chosen fuel stops along the route, each containing station details and the mile marker on the route where the stop is located."""
        
    # If the total route distance is less than or equal to the maximum range of the vehicle, no fuel stops are needed.
    if route_distance_miles <= MAX_RANGE_MILES:
        return []

    # This list will store the chosen fuel stops along the route, and the set will keep track of station IDs that have already been used as stops to avoid duplicates.
    fuel_stops = []
    current_mile = 0
    used_station_ids = set()

    # Sort the nearby stations by their mile marker on the route to facilitate the selection of stops in order along the route.
    nearby_stations = sorted(
        nearby_stations,
        key=lambda station: station["route_mile"]
    )

    # Loop through the route distance, starting from the current mile marker, and at each step, look for candidate stations that are within the defined minimum progress miles and maximum range miles from the current mile marker. If no candidates are found within the ideal range, expand the search to include stations that are just beyond the current mile marker up to the maximum range. From the candidate stations, select the one with the lowest fuel price as the next stop, add it to the list of fuel stops, mark it as used, and update the current mile marker to the mile marker of the chosen station. Repeat this process until the end of the route is reached or no more suitable stations are available.
    while current_mile + MAX_RANGE_MILES < route_distance_miles:
        min_mile = current_mile + MIN_PROGRESS_MILES
        max_mile = current_mile + MAX_RANGE_MILES

        candidates = []

        for station in nearby_stations:
            station_id = station.get("id") or station["name"]
            station_mile = station["route_mile"]

            if station_id in used_station_ids:
                continue

            if min_mile <= station_mile <= max_mile:
                candidates.append(station)

        if not candidates:
            for station in nearby_stations:
                station_id = station.get("id") or station["name"]
                station_mile = station["route_mile"]

                if station_id in used_station_ids:
                    continue

                if current_mile < station_mile <= max_mile:
                    candidates.append(station)

        if not candidates:
            break

        best_station = min(candidates, key=lambda station: station["price"])

        fuel_stops.append(best_station)
        used_station_ids.add(best_station.get("id") or best_station["name"])
        current_mile = best_station["route_mile"]

    return fuel_stops


def calculate_total_fuel_cost(route_distance_miles, fuel_stops):
    """Calculate the total fuel cost for the route based on the chosen fuel stops and the total route distance.
    Args:        
        route_distance_miles (float): The total distance of the route in miles.
        fuel_stops (list): A list of dictionaries representing the chosen fuel stops along the route, each containing station details and the mile marker on the route where the stop is located.
    Returns:        
        float: The total fuel cost for the route."""

    # If there are no fuel stops, the total cost is zero since the vehicle can complete the route on a full tank.
    if not fuel_stops:
        return 0

    # Sort the fuel stops by their mile marker on the route to ensure that the cost calculation is done in the correct order along the route.
    fuel_stops = sorted(fuel_stops, key=lambda stop: stop["route_mile"])

    # The capacity of the vehicle's tank in gallons
    tank_capacity_gallons = MAX_RANGE_MILES / MPG
    
    # Start with full tank
    fuel_left_gallons = tank_capacity_gallons

    # The total cost of the route
    total_cost = 0
    
    # This variable will keep track of the current mile marker on the route as we calculate fuel usage and costs at each stop.
    current_mile = 0

    # Loop through each fuel stop, calculate the fuel used to get there from the current position, determine how much fuel needs to be purchased at the stop to reach the next stop or the end of the route, calculate the cost of that fuel, and update the total cost and fuel left in the tank accordingly. Also, store the gallons purchased and fuel cost for each stop in the stop's details for reference.
    for index, stop in enumerate(fuel_stops):
        stop_mile = stop["route_mile"]

        # fuel used from current position to this stop
        miles_to_stop = stop_mile - current_mile
        fuel_used = miles_to_stop / MPG
        fuel_left_gallons -= fuel_used

        # decide next destination: next stop or finish
        if index + 1 < len(fuel_stops):
            next_mile = fuel_stops[index + 1]["route_mile"]
        else:
            next_mile = route_distance_miles

        # calculate fuel needed to get to the next destination
        miles_to_next = next_mile - stop_mile
        fuel_needed_to_next = miles_to_next / MPG

        # buy only the extra fuel needed
        gallons_to_buy = max(0, fuel_needed_to_next - fuel_left_gallons)

        # calculate cost of fuel to buy at this stop and add it to the total cost
        cost = gallons_to_buy * stop["price"]
        total_cost += cost

        # update fuel left after purchase
        fuel_left_gallons += gallons_to_buy

        # store useful details in response
        stop["gallons_purchased"] = round(gallons_to_buy, 2)
        stop["fuel_cost"] = round(cost, 2)

        # update current mile marker to this stop for the next iteration
        current_mile = stop_mile

    return round(total_cost, 2)