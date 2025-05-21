# NSW Car Park Integration for Home Assistant

This integration connects Home Assistant to the NSW Car Park API, providing real-time parking availability for Transport Park&Ride car parks.

## Installation
1. Add this repository as a custom repository in HACS (see below).
2. Install the "NSW Car Park" integration via HACS.
3. Configure the integration with your API key and desired car park facility IDs.

## Obtaining an API Key
1. Register at [Transport for NSW Open Data Hub](https://opendata.transport.nsw.gov.au/).
2. Create an API token in your profile settings.

## Configuration
- During setup, enter your API key and a comma-separated list of facility IDs (e.g., `1,2,3`).
- Edit car park selections via Settings > Devices & Services > NSW Car Park > Edit.

## HACS Custom Repository
To add this integration to HACS:
1. In Home Assistant, go to HACS > Integrations.
2. Click the three dots (top-right) and select "Custom repositories."
3. Enter the repository URL: `https://github.com/your_github_username/nsw-carpark-ha`.
4. Set the category to "Integration."
5. Click "Add," then search for "NSW Car Park" and install.

## Support
For issues, please open a ticket at [GitHub Issues](https://github.com/your_github_username/nsw-carpark-ha/issues).
