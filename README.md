# NSW Car Park Integration for Home Assistant

This integration connects Home Assistant to the NSW Car Park API, providing real-time parking availability for Transport Park&Ride car parks. It dynamically fetches the car park list, allowing users to select multiple car parks during setup and edit selections later.

## Installation
1. Add this repository as a custom repository in HACS (see below).
2. Install the "NSW Car Park" integration via HACS.
3. Configure the integration with your API key and desired car park facility IDs.

## Obtaining an API Key
1. Register at [Transport for NSW Open Data Hub](https://opendata.transport.nsw.gov.au/).
2. Create an API token in your profile settings.

## Configuration
- During setup, enter your API key and a comma-separated list of facility IDs (e.g., `1,2,3`). The integration will display available car parks for reference.
- Edit car park selections via **Settings > Devices & Services > NSW Car Park > Configure**.

## HACS Custom Repository
To add this integration to HACS:
1. In Home Assistant, go to **HACS > Integrations**.
2. Click the three dots (top-right) and select "Custom repositories."
3. Enter the repository URL: `https://github.com/kcoffau/AUS_TfNSW_carparks`.
4. Set the category to "Integration."
5. Click "Add," then search for "NSW Car Park" and click **Download**.
6. Restart Home Assistant (**Settings > System > Restart**).
7. Add the integration via **Settings > Devices & Services > Add Integration**.

## Support
For issues, please open a ticket at [GitHub Issues](https://github.com/kcoffau/AUS_TfNSW_carparks/issues).

## Notes
- Ensure you have a valid API key from Transport for NSW.
- The integration fetches the car park list dynamically, so new car parks are automatically included without code updates.
