""" bunq models """
from enum import Enum
from typing import TypedDict


class BunqApiUrls(TypedDict):
    """oAuth2 urls for a single environment."""

    authorize_url: str
    token_url: str
    api_url: str


class BunqApiEnvironment(Enum):
    """Enum to represent API environment"""

    Sandbox = (1,)
    Production = (2,)


class BunqStatus:
    """Class to hold all bunq information"""

    user_id: str = None
    session_token: str = None
    accounts: list = []
    cards: list = []
    account_transactions: dict = {}

    def update_user(self, user_id, session_token):
        """Store user info."""
        self.user_id = user_id
        self.session_token = session_token

    def update_accounts(self, accounts):
        """Update accounts."""
        self.accounts = accounts

    def update_account_transactions(self, account_id, transactions):
        """Update transactions."""
        self.account_transactions[str(account_id)] = transactions

    def update_cards(self, cards):
        """Update cards."""
        self.cards = cards

    def get_account(self, account_id):
        """Get account from state."""
        for account in self.accounts:
            if str(account["id"]) == str(account_id):
                return account

    def get_card(self, card_id):
        """Get card from state."""
        for card in self.cards:
            if str(card["id"]) == str(card_id):
                return card
