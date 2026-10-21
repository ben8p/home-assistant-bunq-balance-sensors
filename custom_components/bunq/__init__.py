"""Support for bunq account balance."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session, async_get_config_entry_implementation)

from .const import AUTH_TYPE_API_KEY, AUTH_TYPE_OAUTH, CONF_AUTH_TYPE, DOMAIN
from .coordinator import BunqDataUpdateCoordinator
from .services import async_setup_services

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bunq from a config entry."""
    oauth_session = None
    if entry.data.get(CONF_AUTH_TYPE, AUTH_TYPE_OAUTH) != AUTH_TYPE_API_KEY:
        implementation = await async_get_config_entry_implementation(hass, entry)
        oauth_session = OAuth2Session(hass, entry, implementation)
    coordinator = BunqDataUpdateCoordinator(hass, entry=entry, session=oauth_session)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok

