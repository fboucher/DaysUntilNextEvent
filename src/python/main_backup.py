import network
import urequests
import time
import ntptime
from machine import Pin, ADC, reset
import neopixel
import random
import math
import config
import os

# Globals

SSID = config.SSID
PASSWORD = config.PASSWORD
SETTINGSURL = config.SETTINGSURL
PIXELS = config.PIXELS

# Pin Assignment
ldr = ADC(26)  # LDR connected to ADC on GPIO 26
switch = Pin(15, Pin.IN, Pin.PULL_UP)  # Pull-up for momentary switch
np = neopixel.NeoPixel(Pin(28), PIXELS)
led = Pin("LED", Pin.OUT)

# Function to connect to WiFi
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print("Connecting to WiFi...")
        time.sleep(1)
    print("Connected to WiFi:", wlan.ifconfig())


# Function to get timezone using ip-api.com
def get_timezone():
    url = "http://ipwhois.app/json/"
    try:
        print("Fetching timezone from IP...")
        response = urequests.get(url)
        if response.status_code == 200:
            data = response.json()
            timezone = data.get('timezone', None)
            response.close()
            if timezone:
                print(f"Detected timezone: {timezone}")
                return timezone
            else:
                print("Timezone not found in response.")
                return None
        else:
            log_error(f"Error fetching timezone: {response.status_code}")
            response.close()
            return None
    except Exception as e:
        log_error(f"Error retrieving timezone: {e}")
        return None

def get_timezone_offset(timezone):
    url = f"http://worldtimeapi.org/api/timezone/{timezone}"
    try:
        log_msg(f"Fetching timezone offset for timezone: {timezone}")
        response = urequests.get(url)
        if response.status_code == 200:
            data = response.json()
            offset = data['utc_offset']
            # Convert offset from format "+HH:MM" to hours
            hours_offset = int(offset[:3])
            response.close()
            return hours_offset
        else:
            log_error(f"Error fetching timezone offset: {response.status_code}")
            response.close()
            return None
    except Exception as e:
        log_error(f"Exception retrieving timezone offset: {e}")
        return None

def adjust_time_with_offset(current_time, offset):
    adjusted_time = time.mktime(current_time) + offset * 3600
    return time.localtime(adjusted_time)

# Function to get local time using timeapi.io
def get_local_time(timezone):
    url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone}"
    try:
        log_msg(f"Fetching local time for timezone: {timezone}")
        response = urequests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Extract year, month, day directly from the JSON response
            year = data['year']
            month = data['month']
            day = data['day']
            response.close()
            return (year, month, day)
        else:
            log_error(f"Error fetching local time: {response.status_code}")
            response.close()
            return None
    except Exception as e:
        log_error(f"Exception retrieving local time: {e}")
        return None

def get_local_time_with_retries(timezone, retries=3, delay=5):
    for attempt in range(retries):
        local_time = get_local_time(timezone)
        if local_time:
            return local_time
        log_error(f"Attempt {attempt + 1} failed to get local time. Retrying in {delay} seconds...")
        time.sleep(delay)
    log_error("Failed to get local time after multiple attempts.")
    return None



# Function to get lighSettings
def get_light_settings():
    try:
        log_msg(f"Fetching online settings")
        response = urequests.get(SETTINGSURL)
        if response.status_code == 200:
            data = response.json()
            # Extract ImportantDate, PrimaryRGBColor, SecondaryRGBColor directly from the JSON response
            ImportantDate = data['ImportantDate']
            StartFromDay = data['StartFromDay']
            PrimaryRGBColor = data['PrimaryRGBColor']
            SecondaryRGBColor = data['SecondaryRGBColor']
            UseCustomColors = data['UseCustomColors']
            StartTime = data['StartTime']
            EndTime = data['EndTime']
            from_pi = data.get('FromPi', False)
            is_reverse =  data.get('IsReverse', False)
            with_marker =  data.get('WithMarker', True)
            marker_color =  data.get('MarkerRGBColor', (255, 255, 255))
            response.close()
            return (ImportantDate, StartFromDay, PrimaryRGBColor, SecondaryRGBColor, UseCustomColors, StartTime, EndTime, from_pi, is_reverse, with_marker, marker_color)
        else:
            log_error(f"Error fetching online settings: {response.status_code}")
            response.close()
            return None
    except Exception as e:
        log_error(f"Error retrieving online settings: {e}")
        return None    



# Function to convert a string "yyyy-MM-dd" to a date
def string_to_date(date_string):
    year, month, day = map(int, date_string.split('-'))
    return (year, month, day, 0, 0, 0, 0, 0)

# Calculate sleeps until special_day
def days_between_dates(current_date, special_day):
    current_year = current_date[0]
    special_day_struct = time.mktime(string_to_date(special_day))  

    today_struct = time.mktime(current_date + (0, 0, 0, 0, 0))
    sleeps = (special_day_struct - today_struct) // 86400 # seconds in a day
    
    return int(sleeps)


def clamp(value, min_val=0, max_val=255):
    # Clamp a value between min_val and max_val.
    return max(min(int(value), max_val), min_val)


def progress(countdown_days, np, sleeps, spread, light_settings):
    from_pi = light_settings[7]
    is_reverse = light_settings[8]
    with_marker = light_settings[9]
    marker_color = light_settings[10]
    countdown_time = sleeps <= countdown_days

    if countdown_time:
        # Determine range based on whether we want to show days passed or days remaining
        if not is_reverse:
            # Original logic - show days passed (countdown_days down to sleeps)
            day_range = range(countdown_days, sleeps-1, -1)
        else:
            # Reversed logic - show days remaining (sleeps-1 down to 0)
            day_range = range(sleeps-1, -1, -1)
            
        for i in day_range:
            variation_1 = ((countdown_days+1)-i) * random.choice ([-1,1])
            variation_2 = ((countdown_days+1)-i) * random.choice ([-1,1])
            pixelblockchunk = int(PIXELS/countdown_days) # We'll use blocks of this size for the first countdown_days days
            
            if not from_pi:
                # Original direction (start from end of strip)
                pixelblockmax = PIXELS - (countdown_days - i) * pixelblockchunk
                if i>1:
                    pixelblockmin = pixelblockmax - pixelblockchunk
                else:
                    pixelblockmin = 0
            else:
                # Reversed direction (start from beginning of strip)
                pixelblockmin = (countdown_days - i) * pixelblockchunk
                if i>1:
                    pixelblockmax = pixelblockmin + pixelblockchunk
                else:
                    pixelblockmax = PIXELS
            
            for j in range(pixelblockmin, pixelblockmax):
                # Each block drifts at random, clamped between 0 and 255
                r, g, b = np[j]  # The current RGB values of the pixel
                r = clamp(r + variation_1)
                g = clamp(g - variation_1)
                b = clamp(b + variation_2)
                if light_settings[4] == True:
                    if i % 2 == 0:
                        np[j] = string_to_rgb(light_settings[2])
                    else:
                        np[j] = string_to_rgb(light_settings[3])
                else:
                    np[j] = (r,g,b)

            # Add marker LEDs for inactive blocks when with_marker is True
            if with_marker:
                for block in range(countdown_days):
                    if not from_pi:
                        # Original direction (start from end of strip)
                        block_start = PIXELS - (block + 1) * pixelblockchunk
                    else:
                        # Reversed direction (start from beginning of strip)
                        block_start = block * pixelblockchunk
                    # Only set marker if it's outside the current active block
                    if block_start < pixelblockmin or block_start >= pixelblockmax:
                        np[block_start] = string_to_rgb(marker_color)

            
    else:
        # Rest of the function remains unchanged for the breathing effect
        for i in range(PIXELS):
            pixel_index = PIXELS - 1 - i if from_pi else i
            brightness = 32 * (1 + 4 *(math.sin(spread + math.pi)+1)) * math.exp(-(PIXELS/2-i) ** 2 / (1+20*(math.sin(spread)+1)) ** 2)
            np[pixel_index] = (clamp(todays_color_r * brightness), clamp(todays_color_g * brightness), clamp(todays_color_b * brightness))

    np.write()


def string_to_rgb(rgb_string):
    rgb_string = rgb_string.strip("()")
    rgb_components = rgb_string.split(",")
    r = int(rgb_components[0])
    g = int(rgb_components[1])
    b = int(rgb_components[2])
    return (r, g, b)


def lightsout(np):
    for i in range(PIXELS):
        np[i] =  (0,0,0)
    np.write()


# Function to validate that the lightstrip is working
def wake_up_routine(pixels):
    for i in range(pixels):
        np[i] = (0, 255, 0)
        np.write()
        time.sleep_ms(10)

    time.sleep_ms(200)
    np.fill((155, 155, 0))
    np.write()

    time.sleep_ms(200)
    np.fill((0, 0, 255))
    np.write()

    time.sleep_ms(200)
    np.fill((0, 0, 0))
    np.write()


def string_to_date_tuple(date_string):
    year, month, day = map(int, date_string.split('-'))
    return (year, month, day)


def is_within_time_range(start_time, end_time, current_time):
    start_hour, start_minute = map(int, start_time.split(':'))
    end_hour, end_minute = map(int, end_time.split(':'))
    current_hour, current_minute = current_time[3], current_time[4]

    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    current_minutes = current_hour * 60 + current_minute

    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    else:
        return current_minutes >= start_minutes or current_minutes <= end_minutes

def display_error_state():
    np.fill((255, 0, 0))
    np.write()

def log_error(error_msg):
    print(error_msg)
    try:
        f=open('errors.log', 'a')
        f.write(f"{time.time()}: {error_msg}\n")
        f.close()
    except:
        # If we can't write to the log file, at least print to console
        print(f"Failed to log error: {error_msg}")

def log_msg(msg):
    print(msg)
    try:
        f=open('trace.log', 'a')
        f.write(f"{time.time()}: {msg}\n")
        f.close()
    except:
        # If we can't write to the log file, at least print to console
        print(f"Failed to log error: {msg}")


def reset_trace():
    try:
        os.listdir()
        os.remove("trace.log")
    except:
        print(f"No trace yet.")

def reset_log():
    try:
        os.listdir()
        os.remove("errors.log")
    except:
        print(f"No errors yet.")

def show_progress(progress):
    """
    Show progress on the LED strip.
    :param progress: A number between 1 and 10 indicating the progress level.
    """
    if not (1 <= progress <= 10):
        raise ValueError("Progress must be between 1 and 10")

    # Calculate segment size (including 1 LED gap)
    segment_size = PIXELS // 10
    
    # Turn off all LEDs first
    for i in range(PIXELS):
        np[i] = (0, 0, 0)
    
    # Turn on LEDs for each completed segment, with 1 LED gap between segments
    for segment in range(progress):
        segment_start = segment * segment_size
        segment_end = segment_start + segment_size - 1  # Leave 1 LED as gap
        for i in range(segment_start, min(segment_end, PIXELS)):
            np[i] = (0, 255, 0)  # Green color

    np.write()

def set_ntp_time_with_retries(retries=3, delay=5):
    for attempt in range(retries):
        try:
            ntptime.settime()
            return True
        except Exception as e:
            log_error(f"Attempt {attempt + 1} failed to set NTP time: {e}")
            if attempt < retries - 1:  # Don't sleep on the last attempt
                time.sleep(delay)
    log_error("Failed to set NTP time after multiple attempts")
    return False

# Main program
def main():
    global todays_color_r, todays_color_g, todays_color_b  #bedtime, 

    wake_up_routine(PIXELS)

    # Reset trace file
    reset_trace()
    reset_log()

    log_error(f"Starting up...no errors yet.")

    # Initialise local variables
    LDR_THRESHOLD = 700 # The light dependent resistor reading threshold for light/dark
    CONSECUTIVE_COUNT = 25 # Consecutive readings needed to count a reading as 'consistent
    consecutive_light_count = 0  # Counter for consecutive light readings below the threshold
    consecutive_dark_count = 0  # Counter for consecutive light readings below the threshold
    consistent_light = False
    consistent_dark = False
    spread = 0
    dark = False # Assume light
    # bedtime = False  # Bedtime button not pressed
    twopi = math.pi*2
    
    #color of the day
    todays_color_r = random.randrange(1,99) /100
    todays_color_g = random.randrange(1,99) /100
    todays_color_b = random.randrange(1,99) /100
    log_msg(f"today's based color: ({todays_color_r, todays_color_g, todays_color_b})")

    show_progress(2)

    led.on()       		# Turn the LED on
  
    connect_to_wifi(SSID, PASSWORD)
    # Get local time directly using IP

    # Get timezone from IP
    timezone = get_timezone()
    if timezone is None:
        log_error("Could not detect timezone.")
        display_error_state()
        return
    
    log_msg(f"Detected timezone: {timezone}")
    show_progress(3)

    # Get timezone offset
    timezone_offset = get_timezone_offset(timezone)
    if timezone_offset is None:
        log_error("Could not retrieve timezone offset.")
        display_error_state()
        return

    # Get local time using the detected timezone with retries
    current_date = get_local_time_with_retries(timezone)
    if current_date is None:
        display_error_state()
        log_error("Could not retrieve local time.")
        return

    show_progress(4)
    log_msg(f"Current local date: {current_date}")

    set_ntp_time_with_retries()
    show_progress(5)

    # Get Online settings
    light_settings = get_light_settings()
    special_day = light_settings[0]
    start_from_day = light_settings[1]
    primaryRGBColor = light_settings[2]
    secondaryRGBColor = light_settings[3]
    UseCustomColors = light_settings[4]
    start_time = light_settings[5]
    end_time = light_settings[6]
    log_msg(f"Important Date: {light_settings[0]}")
    log_msg(f"Start from Date: {start_from_day}")
    log_msg(f"Primary RGB Color: {primaryRGBColor}")
    log_msg(f"Secondary RGB Color: {secondaryRGBColor}")
    log_msg(f"Use Custom Colors: {UseCustomColors}")

    show_progress(6)

    # Calculate sleeps until special_day
    sleeps = days_between_dates(current_date, special_day)
    log_msg(f"Number of sleeps until special_day: {sleeps}")

    show_progress(7)

    # Calculate how many days in the countdown
    start_from_day_tuple = string_to_date_tuple(start_from_day)
    countdown_days = abs(days_between_dates(start_from_day_tuple, special_day))
    log_msg(f"The full countdown is {countdown_days} days long")

    show_progress(8)

    log_msg(f"Start Time: {start_time}")
    log_msg(f"End Time: {end_time}")

    show_progress(10)
    time.sleep_ms(500)
    lightsout(np)

    log_msg(f"All Set. Starting main loop...")
 
    # sleeps = 1
    iteration_count = 0
    check_every = 10000 # Check every 10,000 iterations
    # Main Loop
    while True:
        spread = (spread +.05) % twopi # The parameter that gets passed to progress for periodic light
        dark = ldr.read_u16() > LDR_THRESHOLD # True if ldr value is read as high
        current_time = time.localtime()
        adjusted_time = adjust_time_with_offset(current_time, timezone_offset)

        if iteration_count % check_every == 0:
            log_msg(f"it's currently: {adjusted_time[3]}:{adjusted_time[4]}")

        if is_within_time_range(start_time, end_time, adjusted_time):
            
            if iteration_count % check_every == 0:
                log_msg('-> lights on!')

            if consistent_dark: #and not bedtime:  # Darkness detected
                progress(countdown_days,np,sleeps,spread,light_settings)
            else:
                if  consistent_light:  # bedtime or
                    lightsout(np)
        else:
            if iteration_count % check_every == 0:  
                log_msg('-> lights off!')
            lightsout(np)

        if consistent_light: #and bedtime:
            # It has been light for multiple consecutive readings following a bedtime button press
            log_msg('Looks like morning. Resetting...')
            reset()
            current_date = get_local_time_with_retries(timezone)
            log_msg(f"Current local date: {current_date}")
            light_settings = get_light_settings()
            special_day = light_settings[0]
            start_from_day = light_settings[1]
            primaryRGBColor = light_settings[2]
            secondaryRGBColor = light_settings[3]
            UseCustomColors = light_settings[4]
            start_time = light_settings[5]
            end_time = light_settings[6]
            sleeps = days_between_dates(current_date, special_day)
            start_from_day_tuple = string_to_date_tuple(start_from_day)
            countdown_days = abs(days_between_dates(start_from_day_tuple, special_day))


        if dark:
            consecutive_light_count = 0  # Reset counter if reading goes above threshold
            consecutive_dark_count += 1
        else:
            consecutive_light_count += 1
            consecutive_dark_count = 0
        consistent_dark = consecutive_dark_count >= CONSECUTIVE_COUNT
        consistent_light = consecutive_light_count >= CONSECUTIVE_COUNT

        iteration_count += 1



# Run the main program
if __name__ == "__main__":
    main()
