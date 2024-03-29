"""Config flow for Bunq."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import \
    AbstractOAuth2FlowHandler

from .bunq_api import BunqApi
from .const import DOMAIN, ENVIRONMENT, LOGGER


class BunqFlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow to handle Bunq OAuth2 authentication."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an oauth config entry or update existing entry for reauth."""
        api = BunqApi(
            environment=ENVIRONMENT,
            token=data["token"]["access_token"],
            session=async_get_clientsession(self.hass),
        )

        status = await api.update()
        if not status.user_id or not status.session_token:
            return self.async_abort(reason="oauth_error")

        if existing_entry := await self.async_set_unique_id(
            status.user_id.lower()
        ):
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_create_entry(title=status.user_id, data=data)
