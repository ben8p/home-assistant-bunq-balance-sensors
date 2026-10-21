"""Provides the Bunq DataUpdateCoordinator."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .bunq_api import BunqApi
from .const import (AUTH_TYPE_API_KEY, AUTH_TYPE_OAUTH, CONF_API_KEY,
                    CONF_AUTH_TYPE, DOMAIN, ENVIRONMENT, LOGGER,
                    UPDATE_INTERVAL)
from .exceptions import BunqApiError
from .models import BunqStatus


class BunqDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Bunq data from single endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
        session: OAuth2Session | None = None,
    ) -> None:
        """Initialize global Bunq data updater."""
        self.session = session
        self.entry = entry

        client_session = async_get_clientsession(hass)
        if entry.data.get(CONF_AUTH_TYPE, AUTH_TYPE_OAUTH) == AUTH_TYPE_API_KEY:
            self.bunq = BunqApi(
                environment=ENVIRONMENT,
                token=entry.data[CONF_API_KEY],
                session=client_session,
            )
        else:

            async def async_token_refresh() -> str:
                await session.async_ensure_token_valid()
                return str(session.token["access_token"])

            self.bunq = BunqApi(
                environment=ENVIRONMENT,
                token=session.token["access_token"],
                session=client_session,
                token_refresh_method=async_token_refresh,
            )

        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)

    async def _async_update_data(self) -> BunqStatus:
        try:
            return await self.bunq.update()
        except BunqApiError as error:
            if error.is_credentials_error():
                raise ConfigEntryAuthFailed(
                    f"bunq rejected the credentials: {error.get_message()}"
                ) from error
            raise UpdateFailed(f"Invalid response from API: {error}") from error
