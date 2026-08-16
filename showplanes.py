# A project by Brian Munger

from winrt.windows.devices.geolocation import (
    Geolocator,
    PositionAccuracy,
    GeolocationAccessStatus
)

from sys import platform
import requests
import math
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

lat = 0.0
lng = 0.0

# Retrieve operating sys specific path
def path_from_os():
    # Linux or Mac
    if platform == "linux" or platform == "linux2" or platform == "darwin":     
        return "/dev/null"
    # Windows
    elif platform == "win32":
        return "NUL"
    # Not recognized -> default Windows
    else:
        print("\nCould not determine operating system. Using default option of Windows.")
        return "NUL"

# Method for setting up the Selenium Webdriver 
def init_webdriver(): 
    # Selenium Options, run headless (in background), ignore errors
    options = Options()
    #options.add_argument("--headless")          # Comment the next two arguments to have the webdriver run on your screen
    options.add_argument("--disable-gpu")
    options.add_argument("start-maximized")
    options.add_experimental_option(
        "prefs", {
            # Block image loading
            "profile.managed_default_content_settings.images": 2,
        }
    )

    # Make Selenium less detectable as bot activity
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Disable Chronium/Selenium log messages
    options.add_argument("--ignore-certificate-errors")
    options.add_argument('--log-level=3') 
    options.add_argument("--disable-logging")  
    options.add_argument("--disable-speech-api")  
    options.add_argument("--disable-features=MediaSessionService,SpeechRecognition")  

    # Chrome web driver set to Selenium Service
    log_path = path_from_os() # send logs to different places (dev/null or NUL) depending on os type
    service = Service(log_path = log_path) 
    driver = webdriver.Chrome(service=service, options=options)

    return driver

# Method for getting the current longitude and latitude of user
def set_user_location():
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
def retreive_flights(driver):
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
        callsign = plane[1].strip() if plane[1] else "N/A"

        alt_m = plane[7] if plane[7] is not None else 0.0
        # Convert from meters to feet
        alt_ft = alt_m * 3.28084    

        origin, dest = find_origin_dest(callsign, driver)

        print(f"{callsign} {alt_ft:.0f} ft from {origin} to {dest}")
        #print(f"{callsign} {alt_ft:.0f} ft:")

def find_origin_dest(callsign, driver):
    origin = "UNKNOWN"
    dest = "UNKNOWN"

    url = f"https://www.flightaware.com/live/flight/{callsign}"
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    code_items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "flightPageSummaryCity")))
    print(len(code_items))
    print(code_items[0].text)
    origin = code_items[0].text
    dest = code_items[1].text

    return origin, dest


# Run in loop displaying the current plane above
if __name__ == "__main__":
    driver = init_webdriver()
    set_user_location()

    while(1) :
        os.system("cls")
        retreive_flights(driver)
        time.sleep(10)

    driver.quit()