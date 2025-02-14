"""Sensor platform for heating_degree_days."""

from datetime import datetime
from statistics import mean

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BASE_TEMPERATURE,
    ATTR_DATE_RANGE,
    ATTR_MEAN_TEMPERATURE,
    DOMAIN,
    SENSOR_TYPE_DAILY,
    SENSOR_TYPE_MONTHLY,
    SENSOR_TYPE_WEEKLY,
)
from .coordinator import HDDDataUpdateCoordinator


def calculate_hdd_from_readings(
    readings: list[tuple[datetime, float]], base_temp: float
) -> float:
    """Calculate HDD using numerical integration of temperature data.

    Args:
        readings: List of tuples containing (timestamp, temperature)
        base_temp: Base temperature for HDD calculation

    Returns:
        float: Calculated HDD value
    """
    if not readings:
        return 0

    # Sort readings by timestamp
    readings.sort(key=lambda x: x[0])

    # Calculate HDD using numerical integration
    total_hdd = 0
    for i in range(len(readings) - 1):
        current_time, current_temp = readings[i]
        next_time, next_temp = readings[i + 1]

        # Calculate time difference in days
        dt = (next_time - current_time).total_seconds() / (24 * 3600)

        # Calculate average temperature deficit for this interval
        # using trapezoidal rule for integration
        temp_deficit = max(0, base_temp - (current_temp + next_temp) / 2)

        # Add contribution to total HDD
        total_hdd += temp_deficit * dt

    return total_hdd


async def get_temperature_readings(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime,
    entity_id: str,
) -> list[tuple[datetime, float]]:
    """Get temperature readings from Home Assistant history.

    Args:
        hass: Home Assistant instance
        start_time: Start time for data collection
        end_time: End time for data collection
        entity_id: Entity ID of the temperature sensor

    Returns:
        List[Tuple[datetime, float]]: List of (timestamp, temperature) tuples
    """
    temp_history = await get_instance(hass).async_add_executor_job(
        get_significant_states, hass, start_time, end_time, [entity_id]
    )

    if not temp_history or entity_id not in temp_history:
        return []

    # Filter and prepare valid temperature readings with timestamps
    readings = [
        (state.last_updated, float(state.state))
        for state in temp_history[entity_id]
        if state.state not in ("unknown", "unavailable")
        and state.state.replace(".", "", 1).isdigit()
    ]

    return readings


async def async_calculate_hdd(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime,
    entity_id: str,
    base_temp: float,
) -> float:
    """Calculate HDD for a given period.

    This function serves as a bridge between Home Assistant's infrastructure
    and the pure HDD calculation logic.
    """
    readings = await get_temperature_readings(hass, start_time, end_time, entity_id)
    return calculate_hdd_from_readings(readings, base_temp)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HDD sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        HDDSensor(coordinator, SENSOR_TYPE_DAILY),
        HDDSensor(coordinator, SENSOR_TYPE_WEEKLY),
        HDDSensor(coordinator, SENSOR_TYPE_MONTHLY),
    ]

    async_add_entities(sensors)


class HDDSensor(CoordinatorEntity, SensorEntity):
    """Representation of a HDD sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "HDD"

    def __init__(
        self,
        coordinator: HDDDataUpdateCoordinator,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{DOMAIN}_{sensor_type}"
        self._attr_name = f"HDD {sensor_type.capitalize()}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return round(self.coordinator.data[self.sensor_type], 2)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BASE_TEMPERATURE: self.coordinator.base_temp,
            ATTR_DATE_RANGE: self._get_date_range(),
            ATTR_MEAN_TEMPERATURE: self._get_mean_temperature(),
        }

    def _get_date_range(self):
        """Get the date range for the current value."""
        if not self.coordinator.temperature_history:
            return "No data"

        dates = [ts.date() for ts, _ in self.coordinator.temperature_history]
        return f"{min(dates)} to {max(dates)}"

    def _get_mean_temperature(self):
        """Get the mean temperature for the period."""
        if not self.coordinator.temperature_history:
            return None

        return round(
            mean([temp for _, temp in self.coordinator.temperature_history]), 1
        )
