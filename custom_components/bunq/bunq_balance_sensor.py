""" bunq sensor"""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import LOGGER


class BunqBalanceSensor(CoordinatorEntity, SensorEntity):
    """Setup bunq balance sensor."""

    def __init__(self, coordinator, account) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = account["id"]
        self.object_id = "bunq_" + account["description"].lower().replace(" ", "_")
        self.entity_description = SensorEntityDescription(
            key=account["id"],
            device_class=SensorDeviceClass.MONETARY,
            icon="mdi:cash-multiple",
            name=account["description"],
            unit_of_measurement=account["currency"],
        )
        self._attr_extra_state_attributes = {
            "account_id": self._attr_unique_id,
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
        LOGGER.debug("update attributes for %s", str(self._attr_unique_id))

        account = self.coordinator.bunq.status.get_account(self._attr_unique_id)
        if account is None:
            LOGGER.debug("no account for id %s", str(self._attr_unique_id))
            self._attr_enabled = False
            return

        transactions = self.coordinator.bunq.status.account_transactions[
            str(self._attr_unique_id)
        ]
        self._attr_enabled = True
        self._attr_native_value = float(account["balance"]["value"])
        self._load_transactions(transactions)

    def _load_transactions(self, transactions):
        """Load transactions."""
        trx = []
        for transaction in transactions:
            item = {
                "amount": float(transaction["amount"]["value"]),
                "currency": transaction["amount"]["currency"],
                "description": transaction["description"],
                "id": transaction["id"],
                "created": transaction["created"],
                "type": transaction["type"],
                "counterparty": transaction["counterparty_alias"]["display_name"],
            }
            trx.append(item)
        self._attr_extra_state_attributes["transactions"] = trx
