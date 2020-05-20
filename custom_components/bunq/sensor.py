"""Support for bunq account balance."""
import logging
import sys
from datetime import timedelta

import homeassistant.helpers.config_validation as config_validation
import voluptuous
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady

from .api import (
    get_account_transactions,
    get_active_accounts,
    set_api_key,
    set_permitted_ips,
    use_sandbox,
)
from .BunqBalanceSensor import BunqBalanceSensor
from .BunqData import BunqData

_CONF_API_KEY = "api_key"
_CONF_PERMITTED_IPS = "permitted_ips"

_UPDATE_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        voluptuous.Required(_CONF_API_KEY): config_validation.string,
        voluptuous.Required(_CONF_PERMITTED_IPS): config_validation.string,
    }
)

_LOGGER = logging.getLogger("bunq")


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up bunq sensors."""
    sensors = []

    use_sandbox(False)
    set_api_key(config[_CONF_API_KEY])
    set_permitted_ips(config[_CONF_PERMITTED_IPS])

    active_accounts = await get_active_accounts(True)

    # create sensors
    try:
        for account in active_accounts:
            transactions = await get_account_transactions(account["id"], False)
            sensor = BunqBalanceSensor(
                account, transactions
            )
            sensors.append(sensor)
    except:
        _LOGGER.error("Error setting up sensor: %s", sys.exc_info()[0])
        raise PlatformNotReady
    async_add_entities(sensors, True)

    # schedule updates for sensors
    data = BunqData(hass, sensors)
    await data.schedule_update(_UPDATE_INTERVAL)
