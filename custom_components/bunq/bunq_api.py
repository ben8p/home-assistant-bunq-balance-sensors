""" Bunq api class """

import asyncio
import json
import random
import socket
from base64 import b64encode
from typing import Awaitable, Callable, Optional

import async_timeout
from aiohttp import ClientError, ClientResponse, ClientSession, hdrs
from Crypto.PublicKey import RSA
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey.RSA import RsaKey
from Cryptodome.Signature import PKCS1_v1_5

from .const import ENVIRONMENT_URLS, LOGGER, BunqApiEnvironment
from .exceptions import (
    BunqApiConnectionError,
    BunqApiConnectionTimeoutError,
    BunqApiError,
    BunqApiRateLimitError,
)
from .models import BunqStatus


class BunqApi:
    """main api class"""

    _close_session: bool = False

    def __init__(
        self,
        *,
        environment: BunqApiEnvironment,
        token: str,
        request_timeout: int = 8,
        session: Optional[ClientSession] = None,
        token_refresh_method: Optional[Callable[[], Awaitable[str]]] = None,
    ) -> None:
        """Initialize connection with the Bunq API."""
        self.keys = None
        self._api_url = ENVIRONMENT_URLS[environment]["api_url"]
        self.status = BunqStatus()
        self._session = session
        self.request_timeout = request_timeout
        self.token = token
        LOGGER.debug("Session token: %s", token)
        self.token_refresh_method = token_refresh_method
        self._request_id = self._get_request_id(20)

    async def close(self) -> None:
        """Close open client session."""
        if self._session and self._close_session:
            await self._session.close()
            LOGGER.debug("Session closed")

    def _get_request_id(self, length):
        rid = ""
        for _ in range(length - 1):
            rid += str(random.randint(0, 10))
        return rid

    async def _request(self, method, uri, **kwargs) -> ClientResponse:
        """Make a request."""
        if self.token_refresh_method is not None:
            self.token = await self.token_refresh_method()
            LOGGER.debug("Token refresh method called")

        url = self._api_url + uri
        headers = dict(kwargs.pop("headers", {}))
        token = kwargs.pop("token", None)
        signature = kwargs.pop("signature", "")

        LOGGER.debug("Executing %s API request to %s", method, url)
        LOGGER.debug("With body %s", str(kwargs.get("json")))

        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "HomeAssistant"
        headers["X-Bunq-Language"] = "en_US"
        headers["X-Bunq-Region"] = "nl_NL"
        headers["X-Bunq-Geolocation"] = "0 0 0 0 000"
        headers["X-Bunq-Client-Signature"] = signature
        if token is not None:
            headers["X-Bunq-Client-Authentication"] = token
        headers["X-Bunq-Client-Request-Id"] = self._request_id

        LOGGER.debug("With headers: %s", str(headers))
        if self._session is None:
            self._session = ClientSession()
            LOGGER.debug("New session created")
            self._close_session = True

        try:
            with async_timeout.timeout(self.request_timeout):
                response = await self._session.request(
                    method,
                    url,
                    **kwargs,
                    headers=headers,
                )
        except asyncio.TimeoutError as exception:
            raise BunqApiConnectionTimeoutError(
                "Timeout occurred while connecting to the Bunq API"
            ) from exception
        except (ClientError, socket.gaierror) as exception:
            raise BunqApiConnectionError(
                "Error occurred while communicating with the Bunq API"
            ) from exception

        content_type = response.headers.get("Content-Type", "")
        # Error handling
        if (response.status // 100) in [4, 5]:
            contents = await response.read()
            response.close()
            LOGGER.debug("Error response (status %d): %s", response.status, contents)
            if response.status == 429:
                raise BunqApiRateLimitError(
                    "Rate limit error has occurred with the Bunq API"
                )

            if content_type == "application/json":
                raise BunqApiError(response.status, json.loads(contents.decode("utf8")))
            raise BunqApiError(response.status, {"message": contents.decode("utf8")})

        # Handle empty response
        if response.status == 204:
            LOGGER.warning(
                "Request to %s resulted in status 204. Your dataset could be out of date",
                url,
            )
            return

        if "application/json" in content_type:
            result = await response.json()
            LOGGER.debug("Response: %s", str(result))
            return result
        result = await response.text()
        LOGGER.debug("Response: %s", str(result))
        return result

    async def update(self) -> BunqStatus:
        """update data from bunq"""
        await self._setup_context()

        await self._update_accounts()

        for account in self.status.accounts:
            await self.update_account_transactions(account["id"])

        await self._update_cards()

        LOGGER.info("Status updated")
        return self.status

    def _get_user_id(self, data):
        for value in data["Response"]:
            if "UserApiKey" in value:
                return value["UserApiKey"]["id"]

    def _get_token(self, data):
        for value in data["Response"]:
            if "Token" in value:
                return value["Token"]["token"]

    def _generate_signature(self, string_to_sign: str, keys: RsaKey) -> str:
        LOGGER.debug("signing %s", string_to_sign)
        bytes_to_sign = string_to_sign.encode()
        signer = PKCS1_v1_5.new(keys)
        digest = SHA256.new()
        digest.update(bytes_to_sign)
        sign = signer.sign(digest)
        return b64encode(sign).decode("utf-8")

    async def _update_accounts(self):
        try:
            LOGGER.debug("Try to update accounts")
            await self._update_accounts_no_retry()
        except BunqApiError as error:
            LOGGER.debug("Received error %s", str(error))
            if error.args[0] == 401:
                LOGGER.debug("Retry to update accounts")
                self.status.update_user(None, None)
                await self._setup_context()
                await self._update_accounts_no_retry()
            else:
                raise

    async def _update_accounts_no_retry(self):
        data = await self._fetch_monetary_accounts()
        LOGGER.debug("get_active_accounts response: %s", data)
        accounts = []
        for value in data["Response"]:
            for account_type in [
                key
                for key in value
                if key
                in [
                    "MonetaryAccountBank",
                    "MonetaryAccountJoint",
                    "MonetaryAccountLight",
                    "MonetaryAccountSavings",
                ]
            ]:
                item = value[account_type]
                if "status" in item and item["status"] == "ACTIVE":
                    accounts.append(item)
        self.status.update_accounts(accounts)

    async def _update_cards(self):
        """update card data from bunq"""
        try:
            LOGGER.debug("Try to update cards")
            await self._update_cards_no_retry()
        except BunqApiError as error:
            LOGGER.debug("Received error %s", str(error))
            if error.args[0] == 401:
                LOGGER.debug("Retry to update cards")
                self.status.update_user(None, None)
                await self._setup_context()
                await self._update_cards_no_retry()
            else:
                raise

    async def _update_cards_no_retry(self):
        data = await self._fetch_cards()
        LOGGER.debug("get cards response: %s", data)
        cards = []
        for value in data["Response"]:
            for card_type in [
                key for key in value if key in ["CardDebit", "CardCredit"]
            ]:
                item = value[card_type]
                if "status" in item and item["status"] == "ACTIVE":
                    cards.append(item)
        self.status.update_cards(cards)

    async def update_account_transactions(self, account_id):
        """Get transactions of an account."""
        data = await self._fetch_monetary_account_transactions(account_id)
        LOGGER.debug("get_account_transactions response: %s", data)
        transactions = []
        for value in data["Response"]:
            if "Payment" in value:
                item = value["Payment"]
                transactions.append(item)
        self.status.update_account_transactions(account_id, transactions)

    async def _fetch_monetary_account_transactions(self, account_id):
        return await self._request(
            hdrs.METH_GET,
            f"/v1/user/{self.status.user_id}/monetary-account/{account_id}/payment",
            token=self.status.session_token,
        )

    async def _fetch_monetary_accounts(self):
        return await self._request(
            hdrs.METH_GET,
            f"/v1/user/{self.status.user_id}/monetary-account",
            token=self.status.session_token,
        )

    async def _fetch_cards(self):
        return await self._request(
            hdrs.METH_GET,
            f"/v1/user/{self.status.user_id}/card",
            token=self.status.session_token,
        )

    async def link_account_to_card(self, card_id, account_id):
        """Link an account to a card."""

        card = self.status.get_card(card_id)
        if card is None:
            raise f"card {card_id} not found"

        pins = card["pin_code_assignment"]
        for pin in pins:
            del pin["id"]
            del pin["created"]
            del pin["updated"]
            del pin["status"]
            if pin["type"] == "PRIMARY":
                pin["monetary_account_id"] = account_id

        body = {"pin_code_assignment": pins}
        str_body = json.dumps(body)
        signature = self._generate_signature(str_body, self.keys)
        result = await self._request(
            hdrs.METH_PUT,
            f"/v1/user/{self.status.user_id}/card/{card_id}",
            token=self.status.session_token,
            signature=signature,
            data=str_body,
        )
        LOGGER.debug("link account response", json.dumps(result))

        return result

    async def transfer(self, from_account_id, to_account_id, amount, message):
        """Transfer funds to one of your own accounts."""

        to_account = self.status.get_account(to_account_id)
        if to_account is None:
            raise f"target account {to_account} not found"

        if "alias" not in to_account or len(to_account["alias"]) == 0:
            raise f"no alias found for {to_account}"
        alias = to_account["alias"][0]

        if "currency" not in to_account:
            raise f"currency not found for {to_account}"

        body = {
            "amount": {"value": str(amount), "currency": to_account["currency"]},
            "counterparty_alias": alias,
            "description": message,
        }
        str_body = json.dumps(body)
        signature = self._generate_signature(str_body, self.keys)
        result = await self._request(
            hdrs.METH_POST,
            f"/v1/user/{self.status.user_id}/monetary-account/{from_account_id}/payment",
            token=self.status.session_token,
            signature=signature,
            data=str_body,
        )
        LOGGER.debug("transfer response", result)
        return result

    async def _setup_context(self):
        if self.status.user_id is not None and self.status.session_token is not None:
            LOGGER.debug("context already available")
            return
        self.keys = RSA.generate(2048)
        # private_key_client = keys.export_key(format='PEM', passphrase=None, pkcs=8).decode('utf-8')
        public_key_client = (
            self.keys.publickey()
            .export_key(format="PEM", passphrase=None, pkcs=8)
            .decode("utf-8")
        )

        installation = await self._request(
            hdrs.METH_POST,
            "/v1/installation",
            json={"client_public_key": public_key_client},
        )
        LOGGER.debug("installation response: %s", installation)
        installation_token = self._get_token(installation)

        body = {
            "description": "Home Assistant",
            "secret": self.token,
        }
        device_server = await self._request(
            hdrs.METH_POST, "/v1/device-server", token=installation_token, json=body
        )
        LOGGER.debug("device-server response: %s", device_server)

        body = {"secret": self.token}
        str_body = json.dumps(body)
        signature = self._generate_signature(str_body, self.keys)
        session_server = await self._request(
            hdrs.METH_POST,
            "/v1/session-server",
            token=installation_token,
            signature=signature,
            data=str_body,
        )

        user_id = self._get_user_id(session_server)
        session_token = self._get_token(session_server)
        self.status.update_user(str(user_id), str(session_token))
        LOGGER.debug("context updated")
