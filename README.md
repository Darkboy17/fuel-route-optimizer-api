# Fuel Route Optimization API

## Overview

This project is a Django-based API that calculates the optimal fuel
stops along a route within the USA. It uses a free routing API to get the
route and then performs local optimization using fuel price data.

------------------------------------------------------------------------

## Features

-   Accepts start and finish coordinates (USA only)
-   Returns route map (GeoJSON)
-   Calculates optimal fuel stops
-   Uses vehicle constraints:
    -   Max range: 500 miles
    -   Mileage: 10 MPG
-   Computes total fuel cost using partial refueling strategy
-   Fast performance (\~1--2s)

------------------------------------------------------------------------

## Tech Stack

-   Python 3.14
-   Django / Django REST Framework
-   OpenRouteService API

------------------------------------------------------------------------

## Setup Instructions

### 1. Clone the repository

``` bash
git clone https://github.com/Darkboy17/fuel-route-optimizer-api
cd fuel-route-optimizer-api
```

### 2. Create virtual environment

``` bash
# macos / linux
python3 -m venv venv
source venv/bin/activate

# windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Get the openroute service API key by signing up here: https://account.heigit.org/signup

Create a `.env` file under the root directory:

``` env
ORS_API_KEY=your_openrouteservice_api_key
```

------------------------------------------------------------------------

### 5. Run migrations

``` bash
python manage.py makemigrations
python manage.py migrate
```

------------------------------------------------------------------------

### 6. Start server

``` bash
python manage.py runserver
```

API will run at:

    http://127.0.0.1:8000/

------------------------------------------------------------------------

## API Usage

### Endpoint

    POST /api/route-fuel/

### Request Body

``` json
{
  "start": [-74.006, 40.7128],
  "finish": [-118.2437, 34.0522]
}
```

### Response

``` json
{
  "distance_miles": 2793.54,
  "fuel_stops": [...],
  "total_fuel_cost": 1112.98,
  "route_map": {...}
}
```

------------------------------------------------------------------------

## Constraints

-   Both start and finish must be within the USA
-   Max driving range per tank: 500 miles

------------------------------------------------------------------------

## Testing

Use Thunder Client or Postman.

Example test cases:

### Short route (\<500 miles)

``` json
{
  "start": [-118.2437, 34.0522],
  "finish": [-117.1611, 32.7157]
}
```

### Medium route

``` json
{
  "start": [-122.3321, 47.6062],
  "finish": [-104.9903, 39.7392]
}
```

### Long route

``` json
{
  "start": [-74.0060, 40.7128],
  "finish": [-118.2437, 34.0522]
}
```

### Invalid (non-USA)

``` json
{
  "start": [-79.3832, 43.6532],
  "finish": [-104.9903, 39.7392]
}
```

------------------------------------------------------------------------
## Additional Feature: Route Visualization

This project also includes a simple Leaflet-based visualization page for viewing the backend API response on a map.

The visualization allows the reviewer to:

- Enter a start location and finish location
- Click **Search for Stations**
- See the route drawn as a blue line on the map
- See the start and finish markers
- See fuel stop markers along the route
- View route distance, number of stops, and total estimated fuel cost

### How to use the visualization

1. Make sure the Django backend is running:

```bash
python manage.py runserver
```

2. Open the visualization HTML file in a browser.

If using VS Code, you can use the **Live Server** extension:

```txt
Right click visualize.html → Open with Live Server
```

3. Enter locations such as:

```txt
Start: Seattle, WA
Finish: Denver, CO
```

4. Click:

```txt
Search for Stations
```

The frontend will call the Django API at:

```txt
http://127.0.0.1:8000/api/route-fuel/
```

and display the optimized route and fuel stops on the map.

### Notes

- The backend returns the route as GeoJSON.
- Leaflet renders the route using `L.geoJSON(...)`.
- Fuel stop coordinates are displayed as map markers.
- This feature is only for demonstration and for confirming accuracy of backend response visually; the main deliverable is the backend API.

------------------------------------------------------------------------
## Performance

-   Local computation: \~100ms--1000ms
-   Total response: \~1--2s
-   Single external API call

------------------------------------------------------------------------

## Notes

-   Fuel optimization uses a greedy strategy
-   Partial refueling reduces cost over full-tank approach

