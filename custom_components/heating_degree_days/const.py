"""Constants for the Heating Degree Days integration."""

from datetime import timedelta

DOMAIN = "heating_degree_days"

CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_BASE_TEMPERATURE = "base_temperature"
CONF_TEMPERATURE_UNIT = "temperature_unit"

DEFAULT_BASE_TEMPERATURE = 19.0
SCAN_INTERVAL = timedelta(hours=1)

# Sensor types
SENSOR_TYPE_DAILY = "daily"
SENSOR_TYPE_WEEKLY = "weekly"
SENSOR_TYPE_MONTHLY = "monthly"

# Attributes
ATTR_BASE_TEMPERATURE = "base_temperature"
ATTR_DATE_RANGE = "date_range"
ATTR_MEAN_TEMPERATURE = "mean_temperature"
