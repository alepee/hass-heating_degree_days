# Heating Degree Days Integration for Home Assistant

This custom integration calculates Heating Degree Days (HDD) based on outdoor temperature measurements. HDDs are a measurement designed to quantify the demand for energy needed to heat a building.

## What are Heating Degree Days?

Heating degree days are a measure of how much (in degrees) and for how long (in days) the outside air temperature was below a certain base temperature. They are commonly used in calculations relating to the energy consumption required to heat buildings.

For example, if you set a base temperature of 19°C (66.2°F):
- If the average temperature for a day is 14°C, that day has 5 heating degree days
- If the average temperature is above the base temperature, that day has 0 heating degree days

## Installation

### Using HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=astrandb&repository=heating_degree_days)

1. Open HACS
2. Click on "Custom Repositories"
3. Add this repository URL
4. Select "Integration" as the category
5. Click "Install"

### Manual Installation

1. Copy the `heating_degree_days` folder from `custom_components` to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click the "+ ADD INTEGRATION" button
3. Search for "Heating Degree Days"
4. Configure:
   - Select your outdoor temperature sensor
   - Set the base temperature
   - Choose your preferred temperature unit (Celsius or Fahrenheit)

## Features

- Calculates daily, weekly, and monthly heating degree days
- Configurable base temperature
- Support for both Celsius and Fahrenheit
- Uses full temperature history for accurate calculations
- Provides additional attributes:
  - Base temperature
  - Date range for the calculation
  - Mean temperature for the period

## Sensors Created

The integration creates three sensors:
- `sensor.heating_degree_days_daily`: HDD for the current day
- `sensor.heating_degree_days_weekly`: HDD for the current week
- `sensor.heating_degree_days_monthly`: HDD for the current month

## Example Usage

Heating degree days can be used to:
- Monitor heating energy requirements
- Compare energy usage between different periods
- Normalize energy consumption data
- Predict heating costs

## Contributing

Feel free to submit issues and pull requests for improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
