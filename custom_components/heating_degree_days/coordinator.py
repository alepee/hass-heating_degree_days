"""DataUpdateCoordinator for heating_degree_days."""

import calendar
from collections import defaultdict
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculations import (
    calculate_cdd_from_readings,
    calculate_hdd_from_readings,
    get_temperature_readings,
)
from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    SENSOR_TYPE_CDD_DAILY,
    SENSOR_TYPE_CDD_MONTHLY,
    SENSOR_TYPE_CDD_WEEKLY,
    SENSOR_TYPE_HDD_DAILY,
    SENSOR_TYPE_HDD_MONTHLY,
    SENSOR_TYPE_HDD_WEEKLY,
)

_LOGGER = logging.getLogger(__name__)


class HDDDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching HDD and CDD data."""

    def __init__(
        self,
        hass: HomeAssistant,
        temp_entity: str,
        base_temp: float,
        temperature_unit: str,
        include_cooling: bool = False,
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
        self.include_cooling = include_cooling
        self.temperature_history = []
        self.daily_values = defaultdict(float)  # Storage for daily values by date
        self.daily_cdd_values = defaultdict(
            float
        )  # Storage for daily CDD values by date

        _LOGGER.info(
            "Initialized HDDDataUpdateCoordinator with sensor %s, base temp %.1f°%s, cooling: %s",
            temp_entity,
            base_temp,
            temperature_unit,
            "enabled" if include_cooling else "disabled",
        )

    async def _async_update_data(self):
        """Update data via library."""
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_date = yesterday_start.date()

        _LOGGER.debug(
            "Starting data update for period %s to %s",
            yesterday_start.isoformat(),
            today_start.isoformat(),
        )

        # Get temperature readings for yesterday (full day)
        daily_readings = await get_temperature_readings(
            self.hass,
            yesterday_start,
            today_start,
            self.temp_entity,
        )

        if not daily_readings:
            _LOGGER.warning(
                "No temperature readings found for %s between %s and %s",
                self.temp_entity,
                yesterday_start.isoformat(),
                today_start.isoformat(),
            )
            return (
                self.data
                if self.data
                else {
                    SENSOR_TYPE_HDD_DAILY: 0,
                    SENSOR_TYPE_HDD_WEEKLY: 0,
                    SENSOR_TYPE_HDD_MONTHLY: 0,
                    SENSOR_TYPE_CDD_DAILY: 0 if self.include_cooling else None,
                    SENSOR_TYPE_CDD_WEEKLY: 0 if self.include_cooling else None,
                    SENSOR_TYPE_CDD_MONTHLY: 0 if self.include_cooling else None,
                }
            )

        _LOGGER.debug("Retrieved %d temperature readings", len(daily_readings))

        # Store the most recent readings for attributes
        self.temperature_history = daily_readings

        # Calculate daily HDD using integration method
        # (Integration method as requested by the user)
        daily_hdd = calculate_hdd_from_readings(daily_readings, self.base_temp)
        daily_cdd = 0

        # Store in daily values history - use yesterday as it's a complete day
        if daily_readings:
            self.daily_values[yesterday_date] = daily_hdd
            _LOGGER.debug(
                "Calculated daily HDD for %s: %.2f (from %d readings)",
                yesterday_date,
                daily_hdd,
                len(daily_readings),
            )

            # Calculate and store CDD if enabled
            if self.include_cooling:
                daily_cdd = calculate_cdd_from_readings(daily_readings, self.base_temp)
                self.daily_cdd_values[yesterday_date] = daily_cdd
                _LOGGER.debug(
                    "Calculated daily CDD for %s: %.2f (from %d readings)",
                    yesterday_date,
                    daily_cdd,
                    len(daily_readings),
                )

        # Clean up old data (keep 60 days maximum)
        old_hdd_count, old_cdd_count = self._cleanup_old_data(60)
        if old_hdd_count or old_cdd_count:
            _LOGGER.debug(
                "Cleaned up %d old HDD values and %d old CDD values",
                old_hdd_count,
                old_cdd_count,
            )

        # Calculate weekly and monthly HDD by summing daily values
        weekly_hdd = self._calculate_current_week_hdd(yesterday_date)
        monthly_hdd = self._calculate_current_month_hdd(yesterday_date)

        _LOGGER.debug(
            "Calculated period values - Weekly HDD: %.2f, Monthly HDD: %.2f",
            weekly_hdd,
            monthly_hdd,
        )

        # Prepare result dict
        result = {
            SENSOR_TYPE_HDD_DAILY: daily_hdd,
            SENSOR_TYPE_HDD_WEEKLY: weekly_hdd,
            SENSOR_TYPE_HDD_MONTHLY: monthly_hdd,
        }

        # Add CDD data if enabled
        if self.include_cooling:
            # Calculate weekly and monthly CDD by summing daily values
            weekly_cdd = self._calculate_current_week_cdd(yesterday_date)
            monthly_cdd = self._calculate_current_month_cdd(yesterday_date)

            _LOGGER.debug(
                "Calculated period values - Weekly CDD: %.2f, Monthly CDD: %.2f",
                weekly_cdd,
                monthly_cdd,
            )

            result.update(
                {
                    SENSOR_TYPE_CDD_DAILY: daily_cdd,
                    SENSOR_TYPE_CDD_WEEKLY: weekly_cdd,
                    SENSOR_TYPE_CDD_MONTHLY: monthly_cdd,
                }
            )

        return result

    def _cleanup_old_data(self, days_to_keep):
        """Remove old data from daily values history."""
        cutoff_date = dt_util.now().date() - timedelta(days=days_to_keep)

        # Count items to be removed for logging
        hdd_before_count = len(self.daily_values)
        cdd_before_count = len(self.daily_cdd_values)

        # Create new dictionaries with only recent values
        self.daily_values = {
            date: value
            for date, value in self.daily_values.items()
            if date >= cutoff_date
        }

        self.daily_cdd_values = {
            date: value
            for date, value in self.daily_cdd_values.items()
            if date >= cutoff_date
        }

        # Return count of removed items
        return (
            hdd_before_count - len(self.daily_values),
            cdd_before_count - len(self.daily_cdd_values),
        )

    def _calculate_current_week_hdd(self, reference_date):
        """Calculate weekly HDD by summing daily values.

        Week is defined as Monday to Sunday.
        """
        # Determine the start of the week (Monday)
        weekday = reference_date.weekday()
        week_start = reference_date - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)

        _LOGGER.debug(
            "Calculating weekly HDD from %s to %s",
            week_start.isoformat(),
            week_end.isoformat(),
        )

        # Check for missing data in the week
        missing_dates = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            if (
                current_date <= dt_util.now().date()
                and current_date not in self.daily_values
            ):
                missing_dates.append(current_date)

        if missing_dates:
            _LOGGER.debug(
                "Missing HDD data for dates in current week: %s",
                ", ".join(date.isoformat() for date in missing_dates),
            )

        # Sum all daily values that fall within this week
        weekly_hdd = 0
        for i in range(7):  # Monday to Sunday
            current_date = week_start + timedelta(days=i)
            daily_value = self.daily_values.get(current_date, 0)
            weekly_hdd += daily_value

        return weekly_hdd

    def _calculate_current_month_hdd(self, reference_date):
        """Calculate monthly HDD by summing daily values.

        Month is defined as 1st to last day of the month.
        """
        # First day of current month
        month_start = reference_date.replace(day=1)

        # Last day of current month
        _, last_day = calendar.monthrange(reference_date.year, reference_date.month)
        month_end = reference_date.replace(day=last_day)

        _LOGGER.debug(
            "Calculating monthly HDD from %s to %s",
            month_start.isoformat(),
            month_end.isoformat(),
        )

        # Check for missing data in the month
        missing_dates = []
        current_date = month_start
        while current_date <= min(dt_util.now().date(), month_end):
            if current_date not in self.daily_values:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        if missing_dates:
            _LOGGER.debug(
                "Missing HDD data for dates in current month: %s",
                ", ".join(date.isoformat() for date in missing_dates[:5])
                + (
                    f" and {len(missing_dates) - 5} more"
                    if len(missing_dates) > 5
                    else ""
                ),
            )

        # Sum all daily values that fall within this month
        monthly_hdd = 0
        current_date = month_start

        while current_date <= month_end:
            monthly_hdd += self.daily_values.get(current_date, 0)
            current_date += timedelta(days=1)

        return monthly_hdd

    def _calculate_current_week_cdd(self, reference_date):
        """Calculate weekly CDD by summing daily values.

        Week is defined as Monday to Sunday.
        """
        # Determine the start of the week (Monday)
        weekday = reference_date.weekday()
        week_start = reference_date - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)

        _LOGGER.debug(
            "Calculating weekly CDD from %s to %s",
            week_start.isoformat(),
            week_end.isoformat(),
        )

        # Check for missing data in the week
        missing_dates = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            if (
                current_date <= dt_util.now().date()
                and current_date not in self.daily_cdd_values
            ):
                missing_dates.append(current_date)

        if missing_dates:
            _LOGGER.debug(
                "Missing CDD data for dates in current week: %s",
                ", ".join(date.isoformat() for date in missing_dates),
            )

        # Sum all daily values that fall within this week
        weekly_cdd = 0
        for i in range(7):  # Monday to Sunday
            current_date = week_start + timedelta(days=i)
            weekly_cdd += self.daily_cdd_values.get(current_date, 0)

        return weekly_cdd

    def _calculate_current_month_cdd(self, reference_date):
        """Calculate monthly CDD by summing daily values.

        Month is defined as 1st to last day of the month.
        """
        # First day of current month
        month_start = reference_date.replace(day=1)

        # Last day of current month
        _, last_day = calendar.monthrange(reference_date.year, reference_date.month)
        month_end = reference_date.replace(day=last_day)

        _LOGGER.debug(
            "Calculating monthly CDD from %s to %s",
            month_start.isoformat(),
            month_end.isoformat(),
        )

        # Check for missing data in the month
        missing_dates = []
        current_date = month_start
        while current_date <= min(dt_util.now().date(), month_end):
            if current_date not in self.daily_cdd_values:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        if missing_dates:
            _LOGGER.debug(
                "Missing CDD data for dates in current month: %s",
                ", ".join(date.isoformat() for date in missing_dates[:5])
                + (
                    f" and {len(missing_dates) - 5} more"
                    if len(missing_dates) > 5
                    else ""
                ),
            )

        # Sum all daily values that fall within this month
        monthly_cdd = 0
        current_date = month_start

        while current_date <= month_end:
            monthly_cdd += self.daily_cdd_values.get(current_date, 0)
            current_date += timedelta(days=1)

        return monthly_cdd
