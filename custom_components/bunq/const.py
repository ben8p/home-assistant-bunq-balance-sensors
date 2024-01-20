"""Constants for bunq integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

from .models import BunqApiEnvironment, BunqApiUrls

DOMAIN: Final = "bunq"

UPDATE_INTERVAL = timedelta(seconds=55)

ENVIRONMENT_URLS = {
    BunqApiEnvironment.Sandbox: BunqApiUrls(
        authorize_url="https://oauth.sandbox.bunq.com/auth",
        token_url="https://api-oauth.sandbox.bunq.com/v1/token",
        api_url="https://public-api.sandbox.bunq.com",
    ),
    BunqApiEnvironment.Production: BunqApiUrls(
        authorize_url="https://oauth.bunq.com/auth",
        token_url="https://api.oauth.bunq.com/v1/token",
        api_url="https://api.bunq.com",
    ),
}

LOGGER = logging.getLogger(__package__)

ENVIRONMENT = BunqApiEnvironment.Production

ATTR_ACCOUNT_ID = "account_id"
ATTR_CARD_ID = "card_id"
ATTR_AMOUNT = "amount"
ATTR_FROM_ACCOUNT_ENTITY = "from_account_entity"
ATTR_TO_ACCOUNT_ENTITY = "to_account_entity"
ATTR_ACCOUNT_ENTITY = "account_entity"
ATTR_CARD_ENTITY = "card_entity"
ATTR_MESSAGE = "message"
