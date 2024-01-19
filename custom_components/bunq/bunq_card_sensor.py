""" bunq sensor"""

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import LOGGER


class BunqCardSensor(CoordinatorEntity, SensorEntity):
    """Setup bunq card sensor."""

    def __init__(self, coordinator, card) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = card["id"]
        self.object_id = "card_" + str(card["id"])
        self.entity_description = SensorEntityDescription(
            key=card["id"],
            name=card["product_type"].lower().capitalize().replace("_", " ")
            + " "
            + str(card["id"]),
            icon="mdi:credit-card",
        )
        self._attr_extra_state_attributes = {
            "expiry_date": card["expiry_date"],
            "card_id": str(card["id"]),
        }
        self._async_update_attrs()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._async_update_attrs()
        self.async_write_ha_state()

    @callback
    def _async_update_attrs(self) -> None:
        """Update sensor attributes."""
        LOGGER.debug(
            "update attributes for %s", self._attr_extra_state_attributes["card_id"]
        )

        card = None
        for value in self.coordinator.bunq.status.cards:
            if str(value["id"]) == self._attr_extra_state_attributes["card_id"]:
                card = value
        self._attr_extra_state_attributes["limit"] = card["card_limit"]["value"]
        self._attr_extra_state_attributes["limit_atm"] = card["card_limit_atm"]["value"]

        # Linked account
        account_id = ""
        if card is None:
            LOGGER.debug(
                "no card for id %s", self._attr_extra_state_attributes["card_id"]
            )
        else:
            for pin in card["pin_code_assignment"]:
                if pin["type"] == "PRIMARY" and pin["status"] == "ACTIVE":
                    account_id = str(pin["monetary_account_id"])
            LOGGER.debug(
                "match account %s with card %s",
                str(account_id),
                self._attr_extra_state_attributes["card_id"],
            )

            if account_id == "":
                LOGGER.debug("no account linked")

            account_entity = ""
            friendly = ""
            if self.hass is None:
                LOGGER.debug("no hass")
            else:
                for e in self.hass.states.async_all():
                    if str(e.attributes.get("account_id")) == account_id:
                        account_entity = e.entity_id
                        friendly = e.attributes.get(
                            "friendly_name"
                        ) or e.attributes.get("name")
            self._attr_native_value = friendly
            self._attr_extra_state_attributes["account_entity"] = account_entity
