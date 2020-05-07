import json
import logging
import random
import sys
from base64 import b64encode

import requests

from Crypto.PublicKey import RSA
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey.RSA import RsaKey
from Cryptodome.Signature import PKCS1_v1_5
from homeassistant.exceptions import PlatformNotReady

_LOGGER = logging.getLogger("bunq")

_GEOLOCATION = "0 0 0 0 000"

_HEADER_DEFAULTS = {
    "Content-Type": "application/json",
    "User-Agent": "HomeAssistant",
    "X-Bunq-Language": "en_US",
    "X-Bunq-Region": "nl_NL",
    "X-Bunq-Geolocation": _GEOLOCATION,
}

_host = ""
_api_key = ""
_permitted_ips = ""


def set_api_key(api_key):
    global _api_key
    _api_key = api_key


def set_permitted_ips(permitted_ips):
    global _permitted_ips
    _permitted_ips = permitted_ips.replace(" ", "").split(",")


def use_sandbox(status):
    global _host
    _host = "https://public-api.sandbox.bunq.com" if status else "https://api.bunq.com"


use_sandbox(False)


def _get_request_id(length):
    id = ""
    for x in range(length - 1):
        id += str(random.randint(0, 10))
    return id


def _get_token(data):
    for value in data["Response"]:
        if "Token" in value:
            return value["Token"]["token"]


def _get_user_id(data):
    for value in data["Response"]:
        if "UserPerson" in value:
            return value["UserPerson"]["id"]


def _generate_signature(string_to_sign: str, keys: RsaKey) -> str:
    bytes_to_sign = string_to_sign.encode()
    signer = PKCS1_v1_5.new(keys)
    digest = SHA256.new()
    digest.update(bytes_to_sign)
    sign = signer.sign(digest)
    return b64encode(sign)


def _setup_context():
    global _request_id
    global _user_id
    global _session_token

    _request_id = _get_request_id(20)
    _user_id = ""
    _session_token = ""

    keys = RSA.generate(2048)
    # private_key_client = keys.export_key(format='PEM', passphrase=None, pkcs=8).decode('utf-8')
    public_key_client = (
        keys.publickey()
        .export_key(format="PEM", passphrase=None, pkcs=8)
        .decode("utf-8")
    )
    installation_token = ""

    try:
        # setup api context
        installation_response = requests.post(
            _host + "/v1/installation",
            data=json.dumps({"client_public_key": public_key_client}),
            headers={
                **_HEADER_DEFAULTS,
                "X-Bunq-Client-Signature": "",
                "X-Bunq-Client-Request-Id": _request_id,
            },
        )
        installation = installation_response.json()
        _LOGGER.debug("installation response: %s", installation)
        installation_token = _get_token(installation)
    except requests.exceptions.HTTPError as http_error:
        _LOGGER.error("Error with installation api (http_error): %s", http_error)
        raise PlatformNotReady
    except requests.exceptions.ConnectionError as connection_error:
        _LOGGER.error(
            "Error with installation api (connection_error): %s", connection_error
        )
        raise PlatformNotReady
    except requests.exceptions.Timeout as timeout_error:
        _LOGGER.error("Error with installation api (timeout_error): %s", timeout_error)
        raise PlatformNotReady
    except requests.exceptions.TooManyRedirects as too_many_redirects_error:
        _LOGGER.error(
            "Error with installation api (too_many_redirects_error): %s",
            too_many_redirects_error,
        )
        raise PlatformNotReady
    except requests.exceptions.RequestException as request_exception:
        _LOGGER.error(
            "Error with installation api (request_exception): %s", request_exception
        )
        raise PlatformNotReady
    except:
        _LOGGER.error(
            "Error with installation api (exception): %s - public_key_client: %s - installation json: %s",
            sys.exc_info()[0],
            public_key_client,
            installation,
        )
        raise PlatformNotReady

    try:
        device_server_response = requests.post(
            _host + "/v1/device-server",
            data=json.dumps(
                {
                    "description": "Home Assistant",
                    "secret": _api_key,
                    "permitted_ips": _permitted_ips,
                }
            ),
            headers={
                **_HEADER_DEFAULTS,
                "X-Bunq-Client-Request-Id": _request_id,
                "X-Bunq-Client-Signature": "",
                "X-Bunq-Client-Authentication": installation_token,
            },
        )
        _LOGGER.debug("device-server response: %s", device_server_response.json())
    except:
        _LOGGER.error("Error with device-server api: %s", sys.exc_info()[0])
        raise PlatformNotReady

    try:
        body = json.dumps({"secret": _api_key})
        signature = _generate_signature(body, keys)
        session_server_response = requests.post(
            _host + "/v1/session-server",
            data=body,
            headers={
                **_HEADER_DEFAULTS,
                "X-Bunq-Client-Request-Id": _request_id,
                "X-Bunq-Client-Signature": signature,
                "X-Bunq-Client-Authentication": installation_token,
            },
        )
        session_server = session_server_response.json()
        _LOGGER.debug("session-server response: %s", session_server)
        _user_id = _get_user_id(session_server)
        _session_token = _get_token(session_server)
    except Exception as exception:
        _LOGGER.error(
            "Error with session-server api: %s - session_server : %s",
            sys.exc_info()[0],
            session_server,
        )
        raise PlatformNotReady


def _fetch_monetary_accounts():
    try:
        response = requests.get(
            _host + "/v1/user/" + str(_user_id) + "/monetary-account",
            headers={
                **_HEADER_DEFAULTS,
                "X-Bunq-Client-Request-Id": _request_id,
                "X-Bunq-Client-Signature": "",
                "X-Bunq-Client-Authentication": _session_token,
            },
        )
    except requests.exceptions.HTTPError as http_error:
        _LOGGER.error("Error with monetary-account api (http_error): %s", http_error)
        raise PlatformNotReady
    except requests.exceptions.ConnectionError as connection_error:
        _LOGGER.error(
            "Error with monetary-account api (connection_error): %s", connection_error
        )
        raise PlatformNotReady
    except requests.exceptions.Timeout as timeout_error:
        _LOGGER.error(
            "Error with monetary-account api (timeout_error): %s", timeout_error
        )
        raise PlatformNotReady
    except requests.exceptions.TooManyRedirects as too_many_redirects_error:
        _LOGGER.error(
            "Error with monetary-account api (too_many_redirects_error): %s",
            too_many_redirects_error,
        )
        raise PlatformNotReady
    except requests.exceptions.RequestException as request_exception:
        _LOGGER.error(
            "Error with monetary-account api (request_exception): %s", request_exception
        )
        raise PlatformNotReady
    except:
        _LOGGER.error(
            "Error with monetary-account api (exception): %s", sys.exc_info()[0]
        )
        raise PlatformNotReady
    return response


def _fetch_monetary_account_transactions(account_id):
    try:
        response = requests.get(
            _host
            + "/v1/user/"
            + str(_user_id)
            + "/monetary-account/"
            + str(account_id)
            + "/payment",
            headers={
                **_HEADER_DEFAULTS,
                "X-Bunq-Client-Request-Id": _request_id,
                "X-Bunq-Client-Signature": "",
                "X-Bunq-Client-Authentication": _session_token,
            },
        )
    except requests.exceptions.HTTPError as http_error:
        _LOGGER.error("Error with payment api (http_error): %s", http_error)
        raise PlatformNotReady
    except requests.exceptions.ConnectionError as connection_error:
        _LOGGER.error("Error with payment api (connection_error): %s", connection_error)
        raise PlatformNotReady
    except requests.exceptions.Timeout as timeout_error:
        _LOGGER.error("Error with payment api (timeout_error): %s", timeout_error)
        raise PlatformNotReady
    except requests.exceptions.TooManyRedirects as too_many_redirects_error:
        _LOGGER.error(
            "Error with payment api (too_many_redirects_error): %s",
            too_many_redirects_error,
        )
        raise PlatformNotReady
    except requests.exceptions.RequestException as request_exception:
        _LOGGER.error(
            "Error with payment api (request_exception): %s", request_exception
        )
        raise PlatformNotReady
    except:
        _LOGGER.error("Error with payment api (exception): %s", sys.exc_info()[0])
        raise PlatformNotReady
    return response


def get_active_accounts(forceNewSession):
    """Get active bunq accounts."""
    if forceNewSession == True:
        _setup_context()
    response = _fetch_monetary_accounts()
    if response.status_code != 200:
        _setup_context()
        response = _fetch_monetary_accounts()
    data = response.json()
    _LOGGER.debug("get_active_accounts response: %s", data)
    accounts = []
    for value in data["Response"]:
        if "MonetaryAccountBank" in value:
            item = value["MonetaryAccountBank"]
            if "status" in item and item["status"] == "ACTIVE":
                accounts.append(item)
    return accounts


def get_account_transactions(account_id, forceNewSession):
    """Get transactions of an account."""
    if forceNewSession == True:
        _setup_context()
    response = _fetch_monetary_account_transactions(account_id)
    if response.status_code != 200:
        _setup_context()
        response = _fetch_monetary_account_transactions(account_id)
    data = response.json()
    _LOGGER.debug("get_account_transactions response: %s", data)
    transactions = []
    for value in data["Response"]:
        if "Payment" in value:
            item = value["Payment"]
            transactions.append(item)
    return transactions
