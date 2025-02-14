"""Heating Degree Days calculation functions."""

from datetime import datetime

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.core import HomeAssistant


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

        # Calculate temperature deficit for this interval
        # using trapezoidal rule for integration
        current_deficit = max(0, base_temp - current_temp)
        next_deficit = max(0, base_temp - next_temp)
        avg_deficit = (current_deficit + next_deficit) / 2

        # Add contribution to total HDD
        total_hdd += avg_deficit * dt

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
