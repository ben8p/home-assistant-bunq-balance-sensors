import voluptuous as vol
from custom_components.bunq.coordinator import BunqDataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from .exceptions import BunqApiError
from .const import (
    ATTR_ACCOUNT_ENTITY,
    ATTR_ACCOUNT_ID,
    ATTR_AMOUNT,
    ATTR_CARD_ENTITY,
    ATTR_CARD_ID,
    ATTR_FROM_ACCOUNT_ENTITY,
    ATTR_MESSAGE,
    ATTR_TO_ACCOUNT_ENTITY,
    DOMAIN,
    LOGGER,
)

SERVICE_TRANSFER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_FROM_ACCOUNT_ENTITY): cv.string,
        vol.Required(ATTR_TO_ACCOUNT_ENTITY): cv.string,
        vol.Required(ATTR_AMOUNT): vol.Coerce(float),
        vol.Optional(ATTR_MESSAGE): cv.string,
    }
)

SERVICE_LINK_ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCOUNT_ENTITY): cv.string,
        vol.Required(ATTR_CARD_ENTITY): cv.string,
    }
)


async def async_setup_services(
    hass: HomeAssistant, coordinator: BunqDataUpdateCoordinator
):
    """Setup services for bunq."""

    async def transfer_service(call):
        """Execute a transfer via bunq."""

        from_account_entity = call.data.get(ATTR_FROM_ACCOUNT_ENTITY)
        to_account_entity = call.data.get(ATTR_TO_ACCOUNT_ENTITY)
        amount = call.data.get(ATTR_AMOUNT)
        message = call.data.get(ATTR_MESSAGE) or ""

        if ATTR_ACCOUNT_ID not in hass.states.get(from_account_entity).attributes:
            raise HomeAssistantError(
                f"Could not find account id for entity {from_account_entity}"
            )
        from_account_id = hass.states.get(from_account_entity).attributes[
            ATTR_ACCOUNT_ID
        ]
        if ATTR_ACCOUNT_ID not in hass.states.get(to_account_entity).attributes:
            raise HomeAssistantError(
                f"Could not find account id for entity {to_account_entity}"
            )
        to_account_id = hass.states.get(to_account_entity).attributes[ATTR_ACCOUNT_ID]

        LOGGER.debug(
            f"transfer {amount} from {from_account_id} to {to_account_id} (message: '{message}')"
        )
        try:
            await coordinator.bunq.transfer(
                from_account_id, to_account_id, amount, message
            )
        except BunqApiError as e:
            raise HomeAssistantError(e.get_message()) from e

    async def link_account_service(call):
        """Link an account to a card."""

        account_entity = call.data.get(ATTR_ACCOUNT_ENTITY)
        card_entity = call.data.get(ATTR_CARD_ENTITY)

        if ATTR_CARD_ID not in hass.states.get(card_entity).attributes:
            raise HomeAssistantError(f"Could not find card id for entity {card_entity}")
        card_id = hass.states.get(card_entity).attributes[ATTR_CARD_ID]

        if ATTR_ACCOUNT_ID not in hass.states.get(account_entity).attributes:
            raise HomeAssistantError(
                f"Could not find account id for entity {account_entity}"
            )
        account_id = hass.states.get(account_entity).attributes[ATTR_ACCOUNT_ID]

        LOGGER.debug(f"Linking account {account_id} to card {card_id}")
        try:
            await coordinator.bunq.link_account_to_card(card_id, account_id)
        except BunqApiError as e:
            raise HomeAssistantError(e.get_message()) from e

    hass.services.async_register(
        DOMAIN,
        "transfer",
        transfer_service,
        schema=SERVICE_TRANSFER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "link_account", link_account_service, schema=SERVICE_LINK_ACCOUNT_SCHEMA
    )
