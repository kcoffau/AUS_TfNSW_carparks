# Transport for NSW Car Park (Park&Ride) Integration for Home Assistant

This integration connects Home Assistant to the Transport for NSW Car Park API, providing real-time parking availability for Park&Ride car parks. It dynamically fetches the car park list, allowing users to select multiple car parks during setup and edit selections later via the UI.


## Buy Me a Coffee
Whilst I built this integration out of frustration of the poorly built iOS app by TfNSW, and it is available for free, it did have a cost associated with the build, getting advice on some of the storage of the data and calls.   If you find it useful, and can afford it, I would love if you could buy me a coffee as a token of appreciation.  Completely voluntary, and thank you in advance.   I would also welcome you to share the integration with friends, and spread the love.
https://buymeacoffee.com/kelcoffey


## Installation
1. Add this repository as a custom repository in HACS (see below).
2. Install the "Transport for NSW Carpark Availability" integration via HACS.
3. Configure the integration with your API key and select car parks from the dropdown.

## Obtaining an API Key
1. Register at [Transport for NSW Open Data Hub](https://opendata.transport.nsw.gov.au/).
2. Create an API token in your profile settings.

## Configuration
- During setup, enter your API key and select car parks from the dropdown list (fetched dynamically from the API).
- Edit car park selections via **Settings > Devices & Services > TfNSW Car Park > Configure**.

## HACS Custom Repository
To add this integration to HACS:
1. In Home Assistant, go to **HACS > Integrations**.
2. Click the three dots (top-right) and select "Custom repositories."
3. Enter the repository URL: `https://github.com/kcoffau/AUS_TfNSW_carparks`.
4. Set the category to "Integration."
5. Click "Add," then search for "TfNSW Car Park" and click **Download**.
6. Restart Home Assistant (**Settings > System > Restart**).
7. Add the integration via **Settings > Devices & Services > Add Integration**.

## Support
For issues, please open a ticket at [GitHub Issues](https://github.com/kcoffau/AUS_TfNSW_carparks/issues).

## Notes
- Ensure you have a valid API key from Transport for NSW.
- The integration fetches the car park list dynamically, so new car parks are automatically included without code updates.
- Debug logs can be enabled in `configuration.yaml`:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.tfnsw_carpark: debug

