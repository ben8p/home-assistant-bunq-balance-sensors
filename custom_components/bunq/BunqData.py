import asyncio
import logging
import sys

from homeassistant.helpers.event import async_track_time_interval

from .api import get_account_transactions, get_active_accounts

_LOGGER = logging.getLogger("bunq")


class BunqData:
    """Get the latest data and updates the sensors."""

    def __init__(self, hass, sensors):
        """Initialize the data object."""
        self._sensors = sensors
        self.data = {}
        self.hass = hass

    async def update_devices(self):
        """Update all sensors."""
        tasks = []

        for sensor in self._sensors:
            if sensor.load_data(self.data):
                transactions = get_account_transactions(sensor.get_account_id(), False)
                sensor.load_transactions(transactions)
                tasks.append(sensor.async_update_ha_state())
        if tasks:
            await asyncio.wait(tasks)

    async def schedule_update(self, update_interval):
        """Schedule an update."""
        async_track_time_interval(self.hass, self.async_update, update_interval)

    async def async_update(self, *_):
        """Update data."""
        accounts = []
        try:
            # get new data from api
            accounts = get_active_accounts(False)
        except:
            _LOGGER.error("Error updating sensor: %s", sys.exc_info()[0])

        # create a dict with account id as key and account data as value
        self.data = {
            account["id"]: float(account["balance"]["value"]) for account in accounts
        }

        # update the sensors
        await self.update_devices()
