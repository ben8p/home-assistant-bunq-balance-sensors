"""oAuth2 functions and classes for Bunq API integration."""
from __future__ import annotations

import sys
from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation, AuthorizationServer, ClientCredential)
from homeassistant.core import HomeAssistant

from .const import ENVIRONMENT, ENVIRONMENT_URLS, LOGGER


class BunqOAuth2Implementation(AuthImplementation):
    """Local OAuth2 implementation for Bunq."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth_domain: str,
        credential: ClientCredential,
    ) -> None:
        """Local Bunq Oauth Implementation."""
        LOGGER.debug(
            "BunqOAuth2Implementation.__init__: environment=%s, authorize_url=%s, token_url=%s",
            ENVIRONMENT,
            ENVIRONMENT_URLS[ENVIRONMENT]["authorize_url"],
            ENVIRONMENT_URLS[ENVIRONMENT]["token_url"],
        )
        super().__init__(
            hass=hass,
            auth_domain=auth_domain,
            credential=credential,
            authorization_server=AuthorizationServer(
                authorize_url=ENVIRONMENT_URLS[ENVIRONMENT]["authorize_url"],
                token_url=ENVIRONMENT_URLS[ENVIRONMENT]["token_url"],
            ),
        )

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {"response_type": "code"}

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Initialize local Bunq API auth implementation."""
        LOGGER.debug(
            "async_resolve_external_data: received external_data keys=%s, state keys=%s",
            list(external_data.keys()) if isinstance(external_data, dict) else type(external_data),
            list(external_data.get("state", {}).keys()) if isinstance(external_data, dict) else "n/a",
        )

        if "state" not in external_data:
            LOGGER.error("async_resolve_external_data: 'state' key missing from external_data. Full keys: %s", list(external_data.keys()))
            raise KeyError("'state' missing from external_data")

        if "redirect_uri" not in external_data["state"]:
            LOGGER.error(
                "async_resolve_external_data: 'redirect_uri' missing from state. State keys: %s",
                list(external_data["state"].keys()),
            )
            raise KeyError("'redirect_uri' missing from state")

        if "code" not in external_data:
            LOGGER.error("async_resolve_external_data: 'code' missing from external_data. Keys: %s", list(external_data.keys()))
            raise KeyError("'code' missing from external_data")

        redirect_uri = external_data["state"]["redirect_uri"]
        LOGGER.debug("async_resolve_external_data: redirect_uri=%s", redirect_uri)

        token_base_url = ENVIRONMENT_URLS[ENVIRONMENT]["token_url"]
        self.token_url = (
            f"{token_base_url}"
            f"?grant_type=authorization_code"
            f"&client_id={self.client_id}"
            f"&client_secret={self.client_secret}"
            f"&code={external_data['code']}"
            f"&redirect_uri={redirect_uri}"
        )
        LOGGER.debug(
            "async_resolve_external_data: requesting token from %s (secret and code redacted)",
            token_base_url,
        )

        try:
            token = await self._token_request({})
        except Exception as err:
            LOGGER.error("async_resolve_external_data: token request failed: %s", err, exc_info=True)
            raise

        LOGGER.debug(
            "async_resolve_external_data: token received, keys=%s",
            list(token.keys()) if isinstance(token, dict) else type(token),
        )

        # Store the redirect_uri (Needed for refreshing token, but not according to oAuth2 spec!)
        token["redirect_uri"] = redirect_uri
        token["expires_in"] = sys.maxsize
        LOGGER.debug("async_resolve_external_data: token resolved successfully")
        return token

    async def _async_refresh_token(self, token: dict) -> dict:
        """Bunq does not provide a way to refresh the token."""
        LOGGER.debug("_async_refresh_token: bunq does not support token refresh, returning existing token")
        return {**token, **token}
