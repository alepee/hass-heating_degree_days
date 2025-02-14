"""DataUpdateCoordinator for heating_degree_days."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculations import calculate_hdd_from_readings, get_temperature_readings
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HDDDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching HDD data."""

    def __init__(
        self,
        hass: HomeAssistant,
        temp_entity: str,
        base_temp: float,
        temperature_unit: str,
    ):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.temp_entity = temp_entity
        self.base_temp = base_temp
        self.temperature_unit = temperature_unit
        self.temperature_history = []

    async def _async_update_data(self):
        """Update data via library."""
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start.replace(day=1)

        # Get temperature readings for each period
        daily_readings = await get_temperature_readings(
            self.hass,
            yesterday_start,
            today_start,
            self.temp_entity,
        )
        weekly_readings = await get_temperature_readings(
            self.hass,
            week_start,
            today_start,
            self.temp_entity,
        )
        monthly_readings = await get_temperature_readings(
            self.hass,
            month_start,
            today_start,
            self.temp_entity,
        )

        # Store the most recent readings for attributes
        self.temperature_history = monthly_readings

        # Calculate HDD for each period
        return {
            "daily": calculate_hdd_from_readings(daily_readings, self.base_temp),
            "weekly": calculate_hdd_from_readings(weekly_readings, self.base_temp),
            "monthly": calculate_hdd_from_readings(monthly_readings, self.base_temp),
        }
