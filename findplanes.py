# A project by Brian Munger

from dataclasses import dataclass
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
from selenium.common.exceptions import TimeoutException

from displayplanes import print_image

lat = 0.0
lng = 0.0

@dataclass
class DisplayOptions:
    radius: int
    show_on_ground: bool
    show_GA: bool
    debug: bool

curr_display_option = DisplayOptions(radius=20, show_on_ground=False, show_GA=False, debug=False)

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
    options.add_argument("--headless")
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

    if (curr_display_option.debug):
        print(f"User location: {lat} {lng}")
        time.sleep(3)


# Method for checking if a callsign may be associated with a GA flight
# NOTE: A lot of these are PHX area specific :)
def possible_ga_flight(callsign):
    if ((callsign[0] == 'N' and callsign[1].isdigit())     # case 1: Nxxxxx (Basic Aircraft Identifier)
        or callsign[:3] == "OXF"                           # case 2: OXFxxxx (Oxford Aviation Academy)
        or callsign[:3] == "ASI"                           # case 3: ASIxxxx (AeroGuard Flight Training Center)
        or callsign[:3] == "NDU"                           # case 4: NDUxxxx (University of North Dakota)
        or callsign[:3] == "SCA"                           # case 5: SCAxxxx (Sierra Charlie Aviation )
        or callsign[:3] == "VWA"):                         # case 6: VWAxxxx (Venture West Aviation)
        return True

    return False


# Method for retreiving flights above the user in a certain radius
def retreive_flights(driver):
    global lat
    global lng

    # Define boundaries
    delta_mi = curr_display_option.radius
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

    # Request (no auth required)
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

    displayed_plane = False

    # Print callsign and altitude
    for plane in data.get("states", []):
        # Aircraft callsign
        callsign = plane[1].strip() if plane[1] else "N/A"
        # Skip empty callsign or Career Track flights (blocked from FlightAware)
        if (callsign == "N/A" or callsign[:3] == "CXK"):
            continue

        if (curr_display_option.show_GA == False and possible_ga_flight(callsign)):
            if (curr_display_option.debug):
                print(f"SKIPPING {callsign} (GA Traffic)...")
            continue

        # Aircraft speed    
        spd_knts = plane[9] * 1.944

        # Aircraft altiitude 
        alt_m = plane[7] if plane[7] is not None else 0.0
        if (curr_display_option.show_on_ground == False and alt_m == 0):
            continue
        # Convert from meters to feet
        alt_ft = (alt_m * 3.28084 )

        ret_code, origin, dest = find_route(callsign, driver)

        if (ret_code == 200):
            acft_type = driver.find_element(By.XPATH, '//*[@id="mainBody"]/div[1]/div[2]/div[4]/div[9]/div[1]/div/div[1]/div[2]/a').text.strip()

            os.system("cls")
            flight_details = (
                f"{callsign} ({acft_type})\n"
                f"{alt_ft:.0f} ft at {spd_knts:.0f} kts\n"
                f"{origin} to {dest}"
            )
            #print(flight_details)
            print_image(f"logos/{callsign[:3].lower()}.png", text=flight_details)
            displayed_plane = True

            # Display one plane per refresh cycle
            time.sleep(5)
            os.system("cls")

    if not displayed_plane:
        print(f"No displayable aircraft currently overhead in a {delta_mi} mi radius")
        time.sleep(5)


# Method for finding the origin and dest airports via FlightAware
def find_route(callsign, driver):
    default = "UNKNOWN"
    origin = default
    dest = default

    # Scrape FlightAware for aircraft origin and destination info
    url = f"https://www.flightaware.com/live/flight/{callsign}"
    driver.get(url)
    wait = WebDriverWait(driver, 4)

    try: 
        # Commercial aircraft 
        code_items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "flightPageSummaryAirportLink")))
        origin = code_items[0].text[-3:]
        dest = code_items[1].text[-3:]

    except TimeoutException:
        try:
            # General aviation aircraft
            if (curr_display_option.show_GA):
                code_items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "displayFlexElementContainer")))
                origin = code_items[0].get_attribute("textContent").strip()

                # Check if destination exists
                if (len(code_items) > 2):
                    dest = code_items[1].get_attribute("textContent").strip()
            else: 
                return 400, default, default
        except TimeoutException:
                # No aircraft info exists (blocked), skipping...
                if(curr_display_option.debug):
                    print(f"SKIPPING {callsign} (Blocked)...")
                # Return error code
                return 404, default, default

    # Ensure origin / dest is not empty or set as "last seen near..."
    if (len(origin) < 1 or origin == "first seen near"):
        origin = default
    if (len(dest) < 1 or dest == "last seen near"):
        dest = default

    # Return success code and origin and dest
    return 200, origin, dest


# Run in loop displaying the current plane above
if __name__ == "__main__":
    driver = init_webdriver()
    set_user_location()

    try: 
        while(1) :
            os.system("cls")
            retreive_flights(driver)
            time.sleep(30)
    except KeyboardInterrupt:
        # Close driver if user ends program run
        driver.quit()
