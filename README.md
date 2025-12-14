# Visual Countdown Days Until Next Event

Inspired by [howmanysleeps](https://github.com/veebch/howmanysleeps) and [hometime](https://github.com/veebch/hometime) from [veebch](https://github.com/veebch) I wanted to create a countdown for any dates that may be important for you and didn't want to use Google calendar (it's a great idea, but I wanted to skip the API settings).

![Raspberry Pi pico and the light using custom colors](medias/light-and-pi.jpg)

## What it is

This project is composed of two parts:
- Python code for your Raspberry Pi
- .NET website to update configuration. This site let you configure:
  - the important date
  - use 2 custom colors or random ones
  - the RGB value for the custom colors 

![screenshot of the configuration website](medias/blazor-website.png)

## What do you need

- [Raspberry Pi Pico](https://www.raspberrypi.com/products/raspberry-pi-pico/)
- [Azure subscription](portal.azure.com)
- BTF-LIGHTING XGB1338(WS2812B) LED Strip DC5V with Individual Addressable LED
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli)

## How to deploy the configuration website

After cloning this repo. From the folder `src/NextEvent/`, use the Azure developer CLI type the initialization command:

```bash
azd init
```

Enter a meanfull name as it will become the name of your resource group in Azure. To deploy use the deployment command:

```bash
azd up
```

You will be asked to specify the Azure subscription and the location. After a few minutes everything should be deployed. Click the URL from the output in the terminal, or retrieve it from the Azure Portal.

## How to setup the Raspberry Pi Pico

You need to edit the file `config.py`.

- Add the information about your WIFI 
<!-- - Update the URL where the settings are saved. That URL is available from the configuration website you just deployed. You can also retreive it from the Azure portal in the Azure storage blade -->
- Update the number of lights your light strip have.

You can use [Thonny](https://thonny.org/) to copy the python code to the device. You need to copy the `main.py` and `config.py`.

## How it works

- The website creates a JSON file and saves it in a publicly accessible Azure storage.
- When the Pi is powers-on, it will:
  - Turn green one by one all the lights of the strip
  - Change a few time the color of the entire light strip, then turn it off
  - Try to connect to the Wi-Fi
  - Check for code updates from GitHub (if auto-update is enabled)
    - **Blue flashing LEDs** indicate a new version is being downloaded and installed
    - The device will automatically reboot after update
  - Retrieve the timezone, current date, and retrieve the settings from the JSON file
  - If the important date is in 24 days or less the countdown will be display using random colors or the colors you specified.
  - If the date is past the light strip will be lit using the bread effect with a color of the day (it's random once a day)

## Auto-Update Feature

The countdown display includes automatic code updates from GitHub:

- **Automatic Updates**: The device checks for new versions on startup
- **Visual Feedback**: Blue flashing LEDs indicate an update is in progress
- **Safe Updates**: Creates automatic backups before applying updates
- **Configuration**: Control updates via the JSON settings:
  ```json
  {
    "AutoUpdate": true,
    "UpdateBranch": "main"
  }
  ```
- **Version Tracking**: Each release has a version number that's automatically checked
- **Rollback**: Previous version backed up as `main_backup_auto.py` if needed

For detailed information about the auto-update system, see [UPDATE_GUIDE.md](src/python/UPDATE_GUIDE.md).


## Little extra

- The website is deployed in Azure Container App with a minimum scalling to zero to save on cost. That may cause and extra delay for loading the site the first time you try to change the settings. It will work just fine and will turn back to "dormant" after a little while.

