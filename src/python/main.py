"""
Days Until Next Event - LED Countdown Display
Raspberry Pi Pico W with NeoPixel LED Strip

This module provides a countdown timer that displays remaining days
until an important event using a NeoPixel LED strip.

Compatible with: MicroPython v1.24.1 on 2024-11-29; Raspberry Pi Pico W with RP2040
"""

import network
import urequests
import time
import ntptime
from machine import Pin, ADC, reset
import neopixel
import random
import math
import os
import config

# Version
VERSION = "1.0.1"

# ============================================================================
# CONSTANTS
# ============================================================================

# WiFi Configuration
SSID = config.SSID
PASSWORD = config.PASSWORD

# LED Strip Configuration
PIXELS = config.PIXELS
SETTINGSURL = config.SETTINGSURL

# Hardware Pin Configuration
LDR_PIN = 26
SWITCH_PIN = 15
NEOPIXEL_PIN = 28

# Light Detection Settings
LDR_THRESHOLD = 700
CONSECUTIVE_READINGS_NEEDED = 25

# Timing
SETTINGS_REFRESH_ITERATIONS = 10000
ANIMATION_SPEED = 0.05

# Colors
COLOR_ERROR = (255, 0, 0)
COLOR_PROGRESS = (0, 255, 0)
COLOR_UPDATE = (0, 0, 255)
COLOR_OFF = (0, 0, 0)

# Update Settings
GITHUB_RAW_URL = "https://raw.githubusercontent.com/fboucher/DaysUntilNextEvent/{branch}/src/python/main.py"
UPDATE_FILE_NEW = "main_new.py"
UPDATE_FILE_BACKUP = "main_backup_auto.py"


# ============================================================================
# UTILITY CLASSES
# ============================================================================

class Logger:
    """Simple logging utility for errors and trace messages."""
    
    ERROR_LOG = 'errors.log'
    TRACE_LOG = 'trace.log'
    
    @staticmethod
    def error(message):
        """Log an error message to both console and file."""
        print(f"ERROR: {message}")
        Logger._write_to_file(Logger.ERROR_LOG, message)
    
    @staticmethod
    def info(message):
        """Log an info message to both console and file."""
        print(f"INFO: {message}")
        Logger._write_to_file(Logger.TRACE_LOG, message)
    
    @staticmethod
    def _write_to_file(filename, message):
        """Write a timestamped message to a file."""
        try:
            with open(filename, 'a') as f:
                f.write(f"{time.time()}: {message}\n")
        except Exception as e:
            print(f"Failed to write to {filename}: {e}")
    
    @staticmethod
    def clear_logs():
        """Clear all log files."""
        for logfile in [Logger.ERROR_LOG, Logger.TRACE_LOG]:
            try:
                os.remove(logfile)
                Logger.info(f"Cleared {logfile}")
            except:
                pass


class DateUtils:
    """Utility functions for date manipulation."""
    
    @staticmethod
    def string_to_date_tuple(date_string):
        """Convert 'YYYY-MM-DD' string to (year, month, day) tuple."""
        year, month, day = map(int, date_string.split('-'))
        return (year, month, day)
    
    @staticmethod
    def string_to_datetime_tuple(date_string):
        """Convert 'YYYY-MM-DD' string to full datetime tuple."""
        year, month, day = map(int, date_string.split('-'))
        return (year, month, day, 0, 0, 0, 0, 0)
    
    @staticmethod
    def days_between(date1_tuple, date2_string):
        """Calculate days between two dates."""
        date1_seconds = time.mktime(date1_tuple + (0, 0, 0, 0, 0))
        date2_seconds = time.mktime(DateUtils.string_to_datetime_tuple(date2_string))
        return int((date2_seconds - date1_seconds) // 86400)
    
    @staticmethod
    def is_within_time_range(start_time_str, end_time_str, current_time_tuple):
        """Check if current time is within the specified range."""
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))
        current_hour, current_minute = current_time_tuple[3], current_time_tuple[4]
        
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        current_minutes = current_hour * 60 + current_minute
        
        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes <= end_minutes
        else:
            # Handle time range that spans midnight
            return current_minutes >= start_minutes or current_minutes <= end_minutes
    
    @staticmethod
    def adjust_time_with_offset(time_tuple, hours_offset):
        """Adjust time tuple by timezone offset in hours."""
        adjusted_seconds = time.mktime(time_tuple) + hours_offset * 3600
        return time.localtime(adjusted_seconds)


class ColorUtils:
    """Utility functions for color manipulation."""
    
    @staticmethod
    def string_to_rgb(rgb_string):
        """Convert '(R,G,B)' string to (r, g, b) tuple."""
        rgb_string = rgb_string.strip("()")
        r, g, b = map(int, rgb_string.split(","))
        return (r, g, b)
    
    @staticmethod
    def clamp(value, min_val=0, max_val=255):
        """Clamp a value between min_val and max_val."""
        return max(min(int(value), max_val), min_val)
    
    @staticmethod
    def random_base_color():
        """Generate a random base color (0.01 to 0.99)."""
        return (
            random.randrange(1, 99) / 100,
            random.randrange(1, 99) / 100,
            random.randrange(1, 99) / 100
        )

    @staticmethod
    def lighten(color, factor):
        """Lighten a color by a factor (1.0 = no change)."""
        r, g, b = color
        r = ColorUtils.clamp(r * factor)
        g = ColorUtils.clamp(g * factor)
        b = ColorUtils.clamp(b * factor)
        return (r, g, b)


# ============================================================================
# HARDWARE CLASSES
# ============================================================================

class WiFiManager:
    """Manages WiFi connectivity."""
    
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
    
    def connect(self):
        """Connect to WiFi - using the simple approach that works."""
        try:
            Logger.info(f"Connecting to WiFi: {self.ssid}")
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            
            # Wait for connection
            while not self.wlan.isconnected():
                Logger.info("Waiting for WiFi connection...")
                time.sleep(1)
            
            config_info = self.wlan.ifconfig()
            Logger.info(f"Connected to WiFi: {config_info}")
            return True
                
        except Exception as e:
            Logger.error(f"WiFi connection exception: {e}")
            return False
    
    def is_connected(self):
        """Check if WiFi is connected."""
        return self.wlan.isconnected()


class LightSensor:
    """Manages the light-dependent resistor (LDR)."""
    
    def __init__(self, pin, threshold=LDR_THRESHOLD, consecutive_needed=CONSECUTIVE_READINGS_NEEDED):
        self.adc = ADC(pin)
        self.threshold = threshold
        self.consecutive_needed = consecutive_needed
        self.consecutive_dark_count = 0
        self.consecutive_light_count = 0
    
    def update(self):
        """Update the sensor state and return (is_dark, consistent_dark, consistent_light)."""
        reading = self.adc.read_u16()
        is_dark = reading > self.threshold
        
        if is_dark:
            self.consecutive_dark_count += 1
            self.consecutive_light_count = 0
        else:
            self.consecutive_light_count += 1
            self.consecutive_dark_count = 0
        
        consistent_dark = self.consecutive_dark_count >= self.consecutive_needed
        consistent_light = self.consecutive_light_count >= self.consecutive_needed
        
        return is_dark, consistent_dark, consistent_light


class LEDStripController:
    """Controls NeoPixel LED strip animations."""
    
    def __init__(self, pin, num_pixels):
        self.np = neopixel.NeoPixel(Pin(pin), num_pixels)
        self.num_pixels = num_pixels
    
    def clear(self):
        """Turn off all LEDs."""
        self.np.fill(COLOR_OFF)
        self.np.write()
    
    def fill(self, color):
        """Fill all LEDs with a color."""
        self.np.fill(color)
        self.np.write()
    
    def set_pixel(self, index, color):
        """Set a single pixel color."""
        if 0 <= index < self.num_pixels:
            self.np[index] = color
    
    def get_pixel(self, index):
        """Get a single pixel color."""
        if 0 <= index < self.num_pixels:
            return self.np[index]
        return COLOR_OFF
    
    def write(self):
        """Update the LED strip with current buffer."""
        self.np.write()
    
    def startup_animation(self):
        """Display a startup animation to verify LEDs work."""
        # Green wave
        for i in range(self.num_pixels):
            self.set_pixel(i, COLOR_PROGRESS)
            self.write()
            time.sleep_ms(10)
        
        time.sleep_ms(200)
        
        # Yellow flash
        self.fill((155, 155, 0))
        time.sleep_ms(200)
        
        # Blue flash
        self.fill((0, 0, 255))
        time.sleep_ms(200)
        
        # Off
        self.clear()
    
    def show_progress(self, step, total_steps=10):
        """Show progress bar (1-10 segments)."""
        if not (1 <= step <= total_steps):
            return
        
        segment_size = self.num_pixels // total_steps
        self.clear()
        
        for segment in range(step):
            segment_start = segment * segment_size
            segment_end = segment_start + segment_size - 1  # Leave 1 LED gap
            for i in range(segment_start, min(segment_end, self.num_pixels)):
                self.set_pixel(i, COLOR_PROGRESS)
        
        self.write()


class UpdateManager:
    """Manages automatic code updates from GitHub."""
    
    def __init__(self, led_controller, current_version=VERSION):
        self.led = led_controller
        self.current_version = current_version
    
    def check_and_update(self, branch="main", auto_update=True):
        """Check for updates and apply if newer version available."""
        if not auto_update:
            Logger.info("Auto-update disabled in settings")
            return False
        
        Logger.info(f"Checking for updates... Current version: {self.current_version}")
        
        try:
            # Fetch remote version
            remote_version = self._get_remote_version(branch)
            if not remote_version:
                Logger.error("Could not fetch remote version")
                return False
            
            Logger.info(f"Remote version: {remote_version}")
            
            # Compare versions
            if remote_version <= self.current_version:
                Logger.info("Already on latest version")
                return False
            
            Logger.info(f"New version available: {remote_version}")
            
            # Flash blue LEDs to indicate update starting
            for _ in range(3):
                self.led.fill(COLOR_UPDATE)
                time.sleep(0.3)
                self.led.clear()
                time.sleep(0.3)
            
            # Download and apply update
            return self._download_and_apply(branch)
            
        except Exception as e:
            Logger.error(f"Update check failed: {e}")
            return False
    
    def _get_remote_version(self, branch):
        """Fetch VERSION constant from remote main.py."""
        url = GITHUB_RAW_URL.format(branch=branch)
        Logger.info(f"Fetching version from: {url}")
        
        try:
            response = urequests.get(url)
            if response.status_code == 200:
                # Read first 1KB to find VERSION
                content = response.text[:1024]
                response.close()
                
                # Parse VERSION line
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('VERSION = '):
                        # Extract version string
                        version = line.split('=')[1].strip().strip('"\'')
                        return version
                
                Logger.error("VERSION not found in remote file")
                return None
            else:
                Logger.error(f"Failed to fetch remote file: {response.status_code}")
                response.close()
                return None
        except Exception as e:
            Logger.error(f"Error fetching remote version: {e}")
            return None
    
    def _download_and_apply(self, branch):
        """Download new main.py and apply update safely."""
        url = GITHUB_RAW_URL.format(branch=branch)
        
        try:
            # Step 1: Download new file
            Logger.info("Downloading new version...")
            self.led.fill(COLOR_UPDATE)
            
            response = urequests.get(url)
            if response.status_code != 200:
                Logger.error(f"Download failed: {response.status_code}")
                response.close()
                return False
            
            content = response.text
            response.close()
            
            # Step 2: Validate downloaded file
            if len(content) < 1000:  # Sanity check
                Logger.error("Downloaded file too small, aborting")
                return False
            
            if 'import network' not in content or 'def main()' not in content:
                Logger.error("Downloaded file missing key components")
                return False
            
            Logger.info(f"Downloaded {len(content)} bytes")
            
            # Step 3: Save as new file
            Logger.info(f"Saving to {UPDATE_FILE_NEW}...")
            with open(UPDATE_FILE_NEW, 'w') as f:
                f.write(content)
            
            # Step 4: Backup current main.py
            Logger.info("Backing up current version...")
            try:
                with open('main.py', 'r') as src:
                    with open(UPDATE_FILE_BACKUP, 'w') as dst:
                        dst.write(src.read())
            except Exception as e:
                Logger.error(f"Backup failed: {e}")
                # Continue anyway - we have the new file
            
            # Step 5: Replace main.py
            Logger.info("Activating new version...")
            try:
                os.remove('main.py')
            except:
                pass
            
            os.rename(UPDATE_FILE_NEW, 'main.py')
            
            Logger.info("Update complete! Rebooting...")
            self.led.fill(COLOR_UPDATE)
            time.sleep(2)
            
            # Step 6: Reboot
            reset()
            
        except Exception as e:
            Logger.error(f"Update failed: {e}")
            # Try to clean up
            try:
                os.remove(UPDATE_FILE_NEW)
            except:
                pass
            return False


# ============================================================================
# API CLASSES
# ============================================================================

class TimeAPI:
    """Handles time-related API calls."""
    
    @staticmethod
    def get_timezone(retries=3):
        """Get timezone from IP geolocation."""
        url = "http://ipwhois.app/json/"
        
        for attempt in range(retries):
            try:
                Logger.info(f"Fetching timezone (attempt {attempt + 1})...")
                response = urequests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    timezone = data.get('timezone', None)
                    response.close()
                    
                    if timezone:
                        Logger.info(f"Detected timezone: {timezone}")
                        return timezone
                else:
                    Logger.error(f"Timezone API error: {response.status_code}")
                    response.close()
            except Exception as e:
                Logger.error(f"Timezone fetch failed: {e}")
            
            if attempt < retries - 1:
                time.sleep(2)
        
        return None
    
    @staticmethod
    def get_timezone_offset(timezone, retries=3):
        """Get UTC offset for a timezone."""
        url = f"http://worldtimeapi.org/api/timezone/{timezone}"
        
        for attempt in range(retries):
            try:
                Logger.info(f"Fetching timezone offset (attempt {attempt + 1})...")
                response = urequests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    offset = data['utc_offset']
                    hours_offset = int(offset[:3])
                    response.close()
                    Logger.info(f"Timezone offset: {hours_offset} hours")
                    return hours_offset
                else:
                    Logger.error(f"Offset API error: {response.status_code}")
                    response.close()
            except Exception as e:
                Logger.error(f"Offset fetch failed: {e}")
            
            if attempt < retries - 1:
                time.sleep(2)
        
        return None
    
    @staticmethod
    def get_local_date(timezone, retries=3):
        """Get local date for a timezone."""
        url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone}"
        
        for attempt in range(retries):
            try:
                Logger.info(f"Fetching local time (attempt {attempt + 1})...")
                response = urequests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    year = data['year']
                    month = data['month']
                    day = data['day']
                    response.close()
                    Logger.info(f"Local date: {year}-{month:02d}-{day:02d}")
                    return (year, month, day)
                else:
                    Logger.error(f"Local time API error: {response.status_code}")
                    response.close()
            except Exception as e:
                Logger.error(f"Local time fetch failed: {e}")
            
            if attempt < retries - 1:
                time.sleep(2)
        
        return None
    
    @staticmethod
    def sync_ntp_time(retries=3):
        """Synchronize time with NTP server."""
        for attempt in range(retries):
            try:
                ntptime.settime()
                Logger.info("NTP time synchronized")
                return True
            except Exception as e:
                Logger.error(f"NTP sync failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        
        return False


class SettingsAPI:
    """Handles fetching settings from remote storage."""
    
    def __init__(self, url):
        self.url = url
    
    def fetch_settings(self, retries=3):
        """Fetch settings from remote URL."""
        for attempt in range(retries):
            try:
                Logger.info(f"Fetching settings (attempt {attempt + 1})...")
                response = urequests.get(self.url)
                
                if response.status_code == 200:
                    data = response.json()
                    response.close()
                    
                    settings = EventSettings(
                        important_date=data.get('ImportantDate'),
                        start_from_day=data.get('StartFromDay'),
                        primary_color=data.get('PrimaryRGBColor'),
                        secondary_color=data.get('SecondaryRGBColor'),
                        use_custom_colors=data.get('UseCustomColors', False),
                        start_time=data.get('StartTime', '00:00'),
                        end_time=data.get('EndTime', '23:59'),
                        from_pi=data.get('FromPi', False),
                        is_reverse=data.get('IsReverse', False),
                        with_marker=data.get('WithMarker', True),
                        marker_color=data.get('MarkerRGBColor', '(255,255,255)'),
                        flash_speed=data.get('flash_speed', data.get('FlashSpeed', 2)),
                        auto_update=data.get('auto_update', data.get('AutoUpdate', True)),
                        update_branch=data.get('update_branch', data.get('UpdateBranch', 'main'))
                    )
                    
                    Logger.info("Settings fetched successfully")
                    return settings
                else:
                    Logger.error(f"Settings API error: {response.status_code}")
                    response.close()
            except Exception as e:
                Logger.error(f"Settings fetch failed: {e}")
            
            if attempt < retries - 1:
                time.sleep(2)
        
        return None


# ============================================================================
# DATA CLASSES
# ============================================================================

class EventSettings:
    """Container for event configuration settings."""
    
    def __init__(self, important_date, start_from_day, primary_color, secondary_color,
                 use_custom_colors, start_time, end_time, from_pi, is_reverse, 
                 with_marker, marker_color, flash_speed=2, auto_update=True, update_branch='main'):
        self.important_date = important_date
        self.start_from_day = start_from_day
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.use_custom_colors = use_custom_colors
        self.start_time = start_time
        self.end_time = end_time
        self.from_pi = from_pi
        self.is_reverse = is_reverse
        self.with_marker = with_marker
        self.marker_color = marker_color
        self.flash_speed = flash_speed
        self.auto_update = auto_update
        self.update_branch = update_branch
    
    def log_settings(self):
        """Log all settings."""
        Logger.info(f"Important Date: {self.important_date}")
        Logger.info(f"Start From: {self.start_from_day}")
        Logger.info(f"Primary Color: {self.primary_color}")
        Logger.info(f"Secondary Color: {self.secondary_color}")
        Logger.info(f"Use Custom Colors: {self.use_custom_colors}")
        Logger.info(f"Time Range: {self.start_time} - {self.end_time}")
        Logger.info(f"From Pi: {self.from_pi}")
        Logger.info(f"Is Reverse: {self.is_reverse}")
        Logger.info(f"With Marker: {self.with_marker}")
        Logger.info(f"Flash Speed (s): {self.flash_speed}")
        Logger.info(f"Auto Update: {self.auto_update}")
        Logger.info(f"Update Branch: {self.update_branch}")


class CountdownState:
    """Manages the state of the countdown display."""
    
    def __init__(self, current_date, settings):
        Logger.info("CountdownState: Initializing...")
        self.current_date = current_date
        self.settings = settings
        
        Logger.info("CountdownState: Calculating days remaining...")
        self.days_remaining = self._calculate_days_remaining()
        Logger.info(f"Days remaining: {self.days_remaining}")
        
        Logger.info("CountdownState: Calculating countdown length...")
        self.countdown_length = self._calculate_countdown_length()
        Logger.info(f"Countdown length: {self.countdown_length}")
        
        Logger.info("CountdownState: Generating base color...")
        self.base_color = ColorUtils.random_base_color()
        Logger.info(f"Base color: {self.base_color}")
        
        self.animation_phase = 0
        # Feature flag (hardcoded until added to settings)
        self.is_flashing = True
        # Swap colors phase control
        self.swap_phase = False
        try:
            self._last_swap_ms = time.ticks_ms()
        except Exception:
            self._last_swap_ms = 0
        Logger.info("CountdownState: Initialization complete")
    
    def _calculate_days_remaining(self):
        """Calculate days until the important date."""
        return DateUtils.days_between(self.current_date, self.settings.important_date)
    
    def _calculate_countdown_length(self):
        """Calculate total countdown length in days."""
        start_date = DateUtils.string_to_date_tuple(self.settings.start_from_day)
        return abs(DateUtils.days_between(start_date, self.settings.important_date))
    
    def update_animation_phase(self):
        """Update the animation phase for smooth effects."""
        self.animation_phase = (self.animation_phase + ANIMATION_SPEED) % (2 * math.pi)
    
    def update_flash_phase(self):
        """Toggle primary/secondary swap every flash_speed seconds."""
        try:
            now = time.ticks_ms()
            interval_ms = int(self.settings.flash_speed * 1000)
            if interval_ms <= 0:
                interval_ms = 2000
            if time.ticks_diff(now, self._last_swap_ms) >= interval_ms:
                self.swap_phase = not self.swap_phase
                self._last_swap_ms = now
        except Exception:
            # Fallback using seconds component
            sec = time.localtime()[5]
            self.swap_phase = (sec // max(1, int(self.settings.flash_speed))) % 2 == 1


# ============================================================================
# ANIMATION ENGINE
# ============================================================================

class AnimationEngine:
    """Handles LED strip animations for the countdown."""
    
    def __init__(self, led_controller, countdown_state):
        self.led = led_controller
        self.state = countdown_state
    
    def render(self):
        """Render the current countdown state to the LED strip."""
        if self.state.days_remaining <= self.state.countdown_length:
            self._render_countdown()
        else:
            self._render_breathing()
        
        self.led.write()
    
    def _render_countdown(self):
        """Render countdown blocks."""
        settings = self.state.settings
        days_remaining = self.state.days_remaining
        countdown_length = self.state.countdown_length
        phase = self.state.animation_phase
        # Alternate flashing group: 0 = primary blocks, 1 = secondary blocks
        flashing_group = 0 if math.sin(phase) >= 0 else 1
        # Gentle pulse factor for active group (gives a Christmas vibe)
        # Use an eased pulse for smoother visual effect
        raw = (math.sin(phase) + 1) / 2  # 0..1
        pulse = raw * raw * (3 - 2 * raw)  # smoothstep ease-in-out
        # Increase brightness difference to make flashing more noticeable (up to +35%)
        lighten_factor = 1.0 + 0.35 * pulse
        
        # Determine which days to show
        if not settings.is_reverse:
            day_range = range(countdown_length, days_remaining - 1, -1)
        else:
            day_range = range(days_remaining - 1, -1, -1)
        
        # Calculate block size
        block_size = self.led.num_pixels // countdown_length
        
        for day_index in day_range:
            # Calculate pixel range for this day block
            if not settings.from_pi:
                # Start from end of strip
                block_max = self.led.num_pixels - (countdown_length - day_index) * block_size
                if day_index > 1:
                    block_min = block_max - block_size
                else:
                    block_min = 0
            else:
                # Start from beginning of strip
                block_min = (countdown_length - day_index) * block_size
                if day_index > 1:
                    block_max = block_min + block_size
                else:
                    block_max = self.led.num_pixels
            
            # Fill block with color
            for pixel in range(block_min, block_max):
                if settings.use_custom_colors:
                    is_primary_block = (day_index % 2 == 0)
                    # Apply swap phase: invert mapping when swap_phase is True
                    if self.state.swap_phase:
                        is_primary_block = not is_primary_block
                    if is_primary_block:
                        color = ColorUtils.string_to_rgb(settings.primary_color)
                    else:
                        color = ColorUtils.string_to_rgb(settings.secondary_color)
                    # Apply flashing alternance
                    if self.state.is_flashing:
                        if (flashing_group == 0 and is_primary_block) or (flashing_group == 1 and not is_primary_block):
                            color = ColorUtils.lighten(color, lighten_factor)
                else:
                    # Animated color variation
                    variation_1 = ((countdown_length + 1) - day_index) * random.choice([-1, 1])
                    variation_2 = ((countdown_length + 1) - day_index) * random.choice([-1, 1])
                    r, g, b = self.led.get_pixel(pixel)
                    r = ColorUtils.clamp(r + variation_1)
                    g = ColorUtils.clamp(g - variation_1)
                    b = ColorUtils.clamp(b + variation_2)
                    color = (r, g, b)
                    # Even without custom colors, gently flash blocks by parity
                    if self.state.is_flashing:
                        is_primary_block = (day_index % 2 == 0)
                        # Apply swap phase: invert mapping when swap_phase is True
                        if self.state.swap_phase:
                            is_primary_block = not is_primary_block
                        if (flashing_group == 0 and is_primary_block) or (flashing_group == 1 and not is_primary_block):
                            color = ColorUtils.lighten(color, lighten_factor)
                
                self.led.set_pixel(pixel, color)
            
            # Add marker LEDs if enabled
            if settings.with_marker:
                for block in range(countdown_length):
                    if not settings.from_pi:
                        block_start = self.led.num_pixels - (block + 1) * block_size
                    else:
                        block_start = block * block_size
                    
                    # Only mark inactive blocks
                    if block_start < block_min or block_start >= block_max:
                        marker_rgb = ColorUtils.string_to_rgb(settings.marker_color)
                        self.led.set_pixel(block_start, marker_rgb)
    
    def _render_breathing(self):
        """Render breathing animation when event arrives."""
        settings = self.state.settings
        base_r, base_g, base_b = self.state.base_color
        phase = self.state.animation_phase
        
        for i in range(self.led.num_pixels):
            pixel_index = self.led.num_pixels - 1 - i if settings.from_pi else i
            
            # Calculate breathing brightness
            brightness = 32 * (1 + 4 * (math.sin(phase + math.pi) + 1)) * \
                        math.exp(-(self.led.num_pixels / 2 - i) ** 2 / \
                        (1 + 20 * (math.sin(phase) + 1)) ** 2)
            
            color = (
                ColorUtils.clamp(base_r * brightness),
                ColorUtils.clamp(base_g * brightness),
                ColorUtils.clamp(base_b * brightness)
            )
            
            self.led.set_pixel(pixel_index, color)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class CountdownApplication:
    """Main application controller."""
    
    def __init__(self):
        # Initialize hardware
        self.led_controller = LEDStripController(NEOPIXEL_PIN, PIXELS)
        self.light_sensor = LightSensor(LDR_PIN)
        self.onboard_led = Pin("LED", Pin.OUT)
        self.wifi = WiFiManager(SSID, PASSWORD)
        
        # Initialize APIs
        self.settings_api = SettingsAPI(SETTINGSURL)
        
        # State
        self.countdown_state = None
        self.timezone = None
        self.timezone_offset = None
        self.animation_engine = None
        self.iteration_count = 0
    
    def startup(self):
        """Perform startup sequence."""
        Logger.clear_logs()
        Logger.info("=== Countdown Application Starting ===")
        
        self.led_controller.startup_animation()
        self.onboard_led.on()
        
        # Step 1: Connect to WiFi
        self.led_controller.show_progress(1)
        if not self.wifi.connect():
            self._error_state("WiFi connection failed")
            return False
        
        # Step 1.5: Check for updates (before loading settings to get update preferences)
        # First fetch settings to see if auto-update is enabled
        Logger.info("Fetching settings for update check...")
        temp_settings = self.settings_api.fetch_settings()
        if temp_settings and temp_settings.auto_update:
            Logger.info(f"Auto-update enabled, checking for updates from branch: {temp_settings.update_branch}")
            update_manager = UpdateManager(self.led_controller)
            if update_manager.check_and_update(temp_settings.update_branch, temp_settings.auto_update):
                # Device will reboot if update was applied
                # This line will never execute if update successful
                return False
            Logger.info("No update available or update check completed")
        else:
            Logger.info("Auto-update disabled, skipping update check")
        
        # Step 2: Get timezone
        self.led_controller.show_progress(2)
        self.timezone = TimeAPI.get_timezone()
        if not self.timezone:
            self._error_state("Failed to get timezone")
            return False
        
        # Step 3: Get timezone offset
        self.led_controller.show_progress(3)
        self.timezone_offset = TimeAPI.get_timezone_offset(self.timezone)
        if self.timezone_offset is None:
            self._error_state("Failed to get timezone offset")
            return False
        
        # Step 4: Get local date
        self.led_controller.show_progress(4)
        current_date = TimeAPI.get_local_date(self.timezone)
        if not current_date:
            self._error_state("Failed to get local date")
            return False
        
        # Step 5: Sync NTP time
        self.led_controller.show_progress(5)
        TimeAPI.sync_ntp_time()
        
        # Step 6: Fetch settings
        self.led_controller.show_progress(6)
        settings = self.settings_api.fetch_settings()
        if not settings:
            self._error_state("Failed to fetch settings")
            return False
        
        settings.log_settings()
        
        # Step 7: Initialize countdown state
        self.led_controller.show_progress(7)
        Logger.info("Startup: Creating CountdownState...")
        self.countdown_state = CountdownState(current_date, settings)
        Logger.info("Startup: CountdownState created successfully")
        
        # Step 8: Initialize animation engine
        self.led_controller.show_progress(8)
        Logger.info("Startup: Creating AnimationEngine...")
        self.animation_engine = AnimationEngine(self.led_controller, self.countdown_state)
        Logger.info("Startup: AnimationEngine created successfully")
        
        # Complete
        self.led_controller.show_progress(10)
        time.sleep_ms(500)
        self.led_controller.clear()
        
        Logger.info("=== Startup Complete ===")
        return True
    
    def run(self):
        """Main application loop."""
        Logger.info("Starting main loop...")
        
        while True:
            try:
                self._main_loop_iteration()
            except Exception as e:
                Logger.error(f"Error in main loop: {e}")
                time.sleep(1)
    
    def _main_loop_iteration(self):
        """Single iteration of the main loop."""
        # Update animation phase
        self.countdown_state.update_animation_phase()
        self.countdown_state.update_flash_phase()
        
        # Read light sensor
        is_dark, consistent_dark, consistent_light = self.light_sensor.update()
        
        # Get current time
        current_time = time.localtime()
        adjusted_time = DateUtils.adjust_time_with_offset(current_time, self.timezone_offset)
        
        # Log periodically
        if self.iteration_count % SETTINGS_REFRESH_ITERATIONS == 0:
            Logger.info(f"Current time: {adjusted_time[3]:02d}:{adjusted_time[4]:02d}")
        
        # Check if we should display lights
        in_time_range = DateUtils.is_within_time_range(
            self.countdown_state.settings.start_time,
            self.countdown_state.settings.end_time,
            adjusted_time
        )
        
        if in_time_range:
            if self.iteration_count % SETTINGS_REFRESH_ITERATIONS == 0:
                Logger.info("-> Lights ON (in time range)")
            
            if consistent_dark:
                self.animation_engine.render()
            elif consistent_light:
                self.led_controller.clear()
        else:
            if self.iteration_count % SETTINGS_REFRESH_ITERATIONS == 0:
                Logger.info("-> Lights OFF (outside time range)")
            self.led_controller.clear()
        
        # Check if we should refresh settings (new day detected)
        if consistent_light and in_time_range:
            Logger.info("New day detected - refreshing settings...")
            self._refresh_settings()
        
        self.iteration_count += 1
    
    def _refresh_settings(self):
        """Refresh all settings and state."""
        # Get new date
        current_date = TimeAPI.get_local_date(self.timezone)
        if not current_date:
            Logger.error("Failed to refresh date")
            return
        
        # Fetch new settings
        settings = self.settings_api.fetch_settings()
        if not settings:
            Logger.error("Failed to refresh settings")
            return
        
        # Update state
        self.countdown_state = CountdownState(current_date, settings)
        self.animation_engine = AnimationEngine(self.led_controller, self.countdown_state)
        
        Logger.info("Settings refreshed successfully")
    
    def _error_state(self, message):
        """Display error state."""
        Logger.error(message)
        self.led_controller.fill(COLOR_ERROR)


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point."""
    app = CountdownApplication()
    
    if app.startup():
        app.run()
    else:
        Logger.error("Startup failed - halting")
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
