# A project by Brian Munger

from winrt.windows.devices.geolocation import (
    Geolocator,
    PositionAccuracy,
    GeolocationAccessStatus
)

import requests
import math
import time
import os

lat = 0.0
lng = 0.0

# Method for getting the current longitude and latitude of user
def get_user_location():
    global lat
    global lng 

    # Request permission to access Windows location services
    access = Geolocator.request_access_async().get()

    # Throw error if geolocation access is denied 
    if access != GeolocationAccessStatus.ALLOWED:
        print("Unable to access Windows location services.")
        print(f"Permission status: {access}")
        return 
    
    # Create locator object, and set accuracy to high
    locator = Geolocator()
    locator.desired_accuracy = PositionAccuracy.HIGH

    # Get current position
    position = locator.get_geoposition_async().get()
    coordinate = position.coordinate
    lat = round(coordinate.latitude, 2) 
    lng = round(coordinate.longitude, 2)

    print(lat, lng)
    #time.sleep(5)

# Method for getting the origin airport information
def get_origin_airport(icao24):
    now = int(time.time())
    one_hour_ago = now - 3600

    # OpenSky API request URL
    request_url = (
        "https://opensky-network.org/api/flights/aircraft"
        f"?icao24={icao24}"
        f"&begin={one_hour_ago}"
        f"&end={now}"
    )

    # Request (no auth required!)
    res = requests.get(request_url, timeout=10)

    if res.status_code != 200:
        #print(f"Unable to reach OpenSky API. Status {res.status_code}")
        return "Unknown", "Unknown" # Error code 429 = too many requests 
    
    flights = res.json()

    if flights: 
        last = flights[-1]
        return (
            last.get("estDepartureAirport") or "Unknown",
            last.get("estArrivalAirport") or "Unknown"
        )

    return "Unknown", "Unknown"

# Method for retreiving flights above the user in a certain radius
def retreive_flights():
    global lat
    global lng

    # Define boundaries (4 miles)
    delta_mi = 20
    delta_lat = delta_mi / 69.0
    delta_lon = delta_mi / (69.0 * math.cos(math.radians(lat)))

    # OpenSky API request URL
    request_url = (
        "https://opensky-network.org/api/states/all"
        f"?lamin={lat - delta_lat}"
        f"&lomin={lng - delta_lon}"
        f"&lamax={lat + delta_lat}"
        f"&lomax={lng + delta_lon}"
    )

    # Request (no auth required!)
    res = requests.get(request_url, timeout=10)

    # Display error if unable to connect
    if res.status_code != 200:
        print(f"Unable to reach OpenSky API. Status {res.status_code}")
        return

    # Retreive response
    data = res.json()

    # Avoid error if no planes are overhead
    states = data.get("states")
    if not states:
        print(f"No aircraft currently overhead in a {delta_mi} mi radius")
        return

    # Print callsign and altitude
    for plane in data.get("states", []):
        icao24 = plane[0]
        callsign = plane[1].strip() if plane[1] else "N/A"

        alt_m = plane[7] if plane[7] is not None else 0.0
        # Convert from meters to feet
        alt_ft = alt_m * 3.28084    

        dep, arr = get_origin_airport(icao24)

        print(f"{callsign} {alt_ft:.0f} ft from {dep}")

# Run in loop displaying the current plane above
if __name__ == "__main__":
    get_user_location()
    while(1) :
        os.system("cls")
        retreive_flights()
        time.sleep(10)