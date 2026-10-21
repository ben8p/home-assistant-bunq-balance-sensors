"""Config flow for Bunq."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import \
    AbstractOAuth2FlowHandler

from .bunq_api import BunqApi
from .const import (AUTH_TYPE_API_KEY, AUTH_TYPE_OAUTH, CONF_API_KEY,
                    CONF_AUTH_TYPE, DOMAIN, ENVIRONMENT, LOGGER)
from .exceptions import BunqApiConnectionError, BunqApiError
from .models import BunqStatus


class BunqFlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow to handle Bunq authentication (OAuth2 or API key)."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose between OAuth and an API key."""
        return self.async_show_menu(
            step_id="user", menu_options=[AUTH_TYPE_OAUTH, AUTH_TYPE_API_KEY]
        )

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Continue with the OAuth2 flow."""
        return await super().async_step_user(user_input)

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a bunq API key."""
        return await self._async_step_api_key("api_key", user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry.data.get(CONF_AUTH_TYPE) == AUTH_TYPE_API_KEY:
            return await self.async_step_reauth_api_key()
        return await self.async_step_oauth()

    async def async_step_reauth_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a new bunq API key."""
        return await self._async_step_api_key("reauth_api_key", user_input)

    async def _async_step_api_key(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> FlowResult:
        """Validate an API key and create or update the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                status = await self._async_connect(api_key)
            except BunqApiConnectionError:
                errors["base"] = "cannot_connect"
            except BunqApiError as err:
                LOGGER.error("API key validation failed: %s", err.get_message())
                errors["base"] = "invalid_auth"
            else:
                return await self._async_finish(
                    status.user_id,
                    {CONF_AUTH_TYPE: AUTH_TYPE_API_KEY, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def _async_connect(self, token: str) -> BunqStatus:
        """Connect to bunq with the given token and return the fetched status."""
        api = BunqApi(
            environment=ENVIRONMENT,
            token=token,
            session=async_get_clientsession(self.hass),
        )
        status = await api.update()
        if not status.user_id or not status.session_token:
            raise BunqApiError(401, {"message": "no user or session returned"})
        return status

    async def _async_finish(self, user_id: str, data: dict[str, Any]) -> FlowResult:
        """Create the entry, or update the existing one (reauth)."""
        if existing_entry := await self.async_set_unique_id(user_id.lower()):
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_create_entry(title=user_id, data=data)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an oauth config entry or update existing entry for reauth."""
        token = data.get("token", {})
        if not token.get("access_token"):
            LOGGER.error("async_oauth_create_entry: access_token missing from token data")
            return self.async_abort(reason="oauth_error")

        try:
            status = await self._async_connect(token["access_token"])
        except BunqApiError as err:
            LOGGER.error("async_oauth_create_entry: update() failed: %s", err.get_message())
            return self.async_abort(reason="oauth_error")

        return await self._async_finish(
            status.user_id, {**data, CONF_AUTH_TYPE: AUTH_TYPE_OAUTH}
        )
