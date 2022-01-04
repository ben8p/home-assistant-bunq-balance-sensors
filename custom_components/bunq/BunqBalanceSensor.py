import logging

from homeassistant.helpers.entity import Entity

_ICON = "mdi:cash-multiple"

_LOGGER = logging.getLogger("bunq")


class BunqBalanceSensor(Entity):
    """Setup bunq balance sensor."""

    def __init__(self, account, transactions):
        """Initialize the sensor."""
        self.id = account["id"]
        self._name = "bunq_" + account["description"].lower().replace(" ", "_")
        self._state = float(account["balance"]["value"])
        self._unit_of_measurement = account["currency"]
        self.load_transactions(transactions)

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def extra_state_attributes(self):
        attr = dict()
        attr["transactions"] = self._transactions
        attr["account_id"] = self.get_account_id()
        return attr

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the entity icon."""
        return _ICON

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    def get_account_id(self):
        return self.id

    def load_data(self, data):
        """Update sensor data."""
        old_balance = self._state
        self._state = data.get(self.id)
        return self._state == old_balance

    def load_transactions(self, transactions):
        self._transactions = []
        for transaction in transactions:
            _LOGGER.debug("transaction: %s", transaction)
            item = {
                "amount": float(transaction["amount"]["value"]),
                "currency": transaction["amount"]["currency"],
                "description": transaction["description"],
                "id": transaction["id"],
                "created": transaction["created"],
                "type": transaction["type"],
            }
            self._transactions.append(item)
