import geocoder
import requests
import math

def get_user_location():
    location = geocoder.ip('me')
    lat = location.lat
    lng = location.lng
    return lat, lng

def retreive_flights():
    lat, lng = get_user_location()

    # Define boundaries (5 miles)
    delta_mi = 4
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

    # Request (no auth, same as your C++ example)
    res = requests.get(request_url, timeout=10)

    if res.status_code != 200:
        print(f"Unable to reach OpenSky API. Status {res.status_code}")
        return

    data = res.json()

    # Print callsign and altitude
    for plane in data.get("states", []):
        callsign = plane[1].strip() if plane[1] else "N/A"

        alt_m = plane[7] if plane[7] is not None else 0.0
        alt_ft = alt_m * 3.28084

        print(f"{callsign} {alt_ft:.0f} ft")


if __name__ == "__main__":
    retreive_flights()