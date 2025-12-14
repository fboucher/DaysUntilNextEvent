# Days Until Next Event - MicroPython LED Countdown

A countdown timer for Raspberry Pi Pico W that displays remaining days until an important event using a NeoPixel LED strip.

## 📋 Overview

This project has been completely rebuilt from scratch with a focus on:
- **Clean Architecture**: Separated concerns into logical classes
- **Maintainability**: Easy to understand and modify
- **Reliability**: Built-in error handling and retries
- **Flexibility**: Works with any LED strip size (configurable)

## 🎯 Features

- Visual countdown display on NeoPixel LED strips
- Automatic timezone detection and adjustment
- Remote configuration via Azure Blob Storage
- Light-dependent operation (using LDR sensor)
- Scheduled operation (time range control)
- Multiple animation modes:
  - Countdown blocks (with optional markers)
  - Breathing effect when event arrives
  - Custom color schemes
  - Forward/reverse direction support
- Comprehensive logging (errors and traces)
- Automatic daily refresh of settings

## 🔧 Hardware Requirements

- **Raspberry Pi Pico W**
- **NeoPixel LED Strip** (any length - configurable via PIXELS in config.py)
- **LDR (Light Dependent Resistor)** on GPIO 26
- **Optional: Momentary Switch** on GPIO 15 (not used by default)

### Pin Configuration

| Component | GPIO Pin |
|-----------|----------|
| NeoPixel Data | GPIO 28 |
| LDR (ADC) | GPIO 26 |
| Onboard LED | LED |
| Switch (optional, unused by default) | GPIO 15 |

## 📁 Project Structure

### Original Files
- `main_backup.py` - Original monolithic implementation (backup)
- `main_old.py` - Previous version

### Current Files
- `main.py` - **NEW** Refactored, class-based implementation
- `config.py` - Configuration file (WiFi, URL, LED count)

## 🏗️ Architecture

The new code is organized into logical modules:

### Utility Classes
- **`Logger`** - Handles error and trace logging
- **`DateUtils`** - Date manipulation and time range checking
- **`ColorUtils`** - RGB color conversions and clamping

### Hardware Classes
- **`WiFiManager`** - WiFi connectivity with a blocking connect loop and status logs
- **`LightSensor`** - LDR reading with debouncing
- **`LEDStripController`** - Low-level LED strip control

### API Classes
- **`TimeAPI`** - Timezone detection and time synchronization
- **`SettingsAPI`** - Remote configuration fetching

### Data Classes
- **`EventSettings`** - Container for all event configuration
- **`CountdownState`** - Manages countdown calculations and state

### Animation
- **`AnimationEngine`** - Renders countdown and breathing animations

### Main Application
- **`CountdownApplication`** - Orchestrates startup and main loop

## ⚙️ Configuration

Edit `config.py`:

```python
SSID = 'your-wifi-ssid'
PASSWORD = 'your-wifi-password'
SETTINGSURL = "https://your-storage-url/mysettings.json"
PIXELS = 320  # Number of LEDs in your strip
```

## 📊 Remote Settings JSON Format

The remote `mysettings.json` file should contain:

```json
{
  "ImportantDate": "2025-12-25",
  "StartFromDay": "2025-12-01",
  "PrimaryRGBColor": "(255,0,0)",
  "SecondaryRGBColor": "(0,255,0)",
  "UseCustomColors": true,
  "StartTime": "06:00",
  "EndTime": "22:00",
  "FromPi": false,
  "IsReverse": false,
  "WithMarker": true,
  "MarkerRGBColor": "(255,255,255)"
}
```

### Settings Explained

| Setting | Description |
|---------|-------------|
| `ImportantDate` | The target date (YYYY-MM-DD) |
| `StartFromDay` | Countdown start date |
| `PrimaryRGBColor` | First alternating color |
| `SecondaryRGBColor` | Second alternating color |
| `UseCustomColors` | Use custom colors vs animated |
| `StartTime` | Daily start time (HH:MM) |
| `EndTime` | Daily end time (HH:MM) |
| `FromPi` | LED direction (false=end, true=start) |
| `IsReverse` | Reverse countdown direction |
| `WithMarker` | Show marker LEDs between blocks |
| `MarkerRGBColor` | Color for marker LEDs |

## 🚀 How It Works

### Startup Sequence
1. **Visual Animation** - LED wave to verify hardware
2. **WiFi Connection** - Connect to configured network
3. **Timezone Detection** - Auto-detect from IP location
4. **Time Synchronization** - Sync with NTP server
5. **Settings Fetch** - Download configuration from cloud
6. **Countdown Calculation** - Calculate days remaining
7. **Progress Display** - Show 10-step progress bar
8. **Ready** - Enter main loop

### Main Loop
1. Update animation phase
2. Read light sensor (with debouncing)
3. Check current time and time range
4. Render appropriate animation:
   - **Dark + In Range**: Show countdown
   - **Light + In Range**: Turn off LEDs
   - **Outside Range**: Turn off LEDs
5. Refresh settings when consistent light is detected and within the time range (daily refresh trigger)

### Animations

#### Countdown Mode
- LED strip divided into blocks (one per day)
- Active blocks show countdown progress
- Optional marker LEDs between blocks
- Custom or animated color schemes
- Forward or reverse direction

#### Breathing Mode
- Activated when the current date is outside the countdown window (i.e., when `days_remaining > countdown_length`)
- Smooth breathing effect
- Random daily base color
- Gaussian distribution across strip

## 🔍 Improvements Over Original

### Code Quality
- ✅ Separated concerns (network, hardware, animation)
- ✅ Self-documenting class and method names
- ✅ Comprehensive docstrings
- ✅ Constants at top for easy tuning
- ✅ No magic numbers or global variables

### Reliability
- ✅ Retry logic on all network operations
- ✅ Error handling in main loop
- ✅ Graceful degradation
- ✅ Clear error states (red LEDs)

### Maintainability
- ✅ Easy to test individual components
- ✅ Simple to add new features
- ✅ Clear data flow
- ✅ Reusable utility classes

### Performance
- ✅ Reduced redundant calculations
- ✅ Efficient pixel updates
- ✅ Configurable refresh rates

## 🐛 Troubleshooting

### Check Logs
The device creates two log files:
- `errors.log` - Error messages only
- `trace.log` - All info messages

### LED States
- **Green Wave** - Startup animation
- **Red Solid** - Error during startup
- **Green Progress** - Startup progress (1-10 segments)
- **Normal Operation** - Countdown or breathing animation

### Common Issues

**LEDs don't light up**
- Check PIXELS matches your LED count
- Verify NeoPixel pin (GPIO 28)
- Check power supply to LED strip

**WiFi connection fails**
- Verify SSID and PASSWORD in config.py
- Check 2.4GHz WiFi (Pico W doesn't support 5GHz)
- Move closer to router

**Wrong timezone**
- Manually check logs for detected timezone
- IP geolocation may be inaccurate
- Consider hardcoding timezone in TimeAPI

**Settings not loading**
- Verify SETTINGSURL is accessible
- Check JSON format is correct
- Ensure proper CORS settings on blob storage

## 📝 Development Notes

### Adding New Features

**Add a new animation mode:**
1. Add method to `AnimationEngine` class
2. Update `render()` method with condition
3. Add configuration to `EventSettings`

**Add new hardware:**
1. Create class in Hardware section
2. Initialize in `CountdownApplication.__init__()`
3. Use in main loop

**Modify color schemes:**
1. Edit `AnimationEngine._render_countdown()`
2. Or update `ColorUtils` for new utility functions

### Testing Tips

For beginners working with MicroPython:

1. **Test components individually** - Each class can be tested separately
2. **Use REPL** - Connect via USB and test functions interactively
3. **Check logs** - Download and read error.log and trace.log
4. **Small changes** - Make one change at a time
5. **Backup often** - Keep working versions

## 📈 Future Enhancements

Potential improvements:
- Web configuration interface
- Multiple event support
- Custom animation patterns
- Sound/buzzer integration
- Battery power support with sleep modes
- WiFi reconnection handling
- Offline mode with cached settings

## 🎓 Learning Resources

For MicroPython beginners:
- [MicroPython Documentation](https://docs.micropython.org/)
- [Raspberry Pi Pico W Guide](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
- [NeoPixel Guide](https://learn.adafruit.com/adafruit-neopixel-uberguide)

## 📄 License

This is a personal project. Use and modify as needed.

## 🙏 Credits

Rebuilt from original by Frank Boucher
Refactored for clarity, maintainability, and extensibility
