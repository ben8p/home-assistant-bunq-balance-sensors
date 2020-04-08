"""Support for bunq account balance."""
import asyncio
from datetime import timedelta
import logging
import requests
import voluptuous as vol
import random
import sys
import json
from base64 import b64encode
from Crypto.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey.RSA import RsaKey

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

CONF_API_KEY = 'api_key'
CONF_PERMITTED_IPS = 'permitted_ips'

ICON = 'mdi:cash-multiple'
UPDATE_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_PERMITTED_IPS): cv.string,
})

_LOGGER = logging.getLogger(__name__)

PRIVATE_KEY_CLIENT = ''
PUBLIC_KEY_CLIENT = ''
REQUEST_ID = ''
GEOLOCATION = '0 0 0 0 000'
HOST = 'https://api.bunq.com' # 'https://public-api.sandbox.bunq.com'

def get_id(length):
    id = ''
    for x in range(length - 1): 
        id += str(random.randint(0, 10))
    return id

def get_token(data):
    for value in data['Response']:
        if('Token' in value):
            return value['Token']['token']

def get_user_id(data):
    for value in data['Response']:
        if('UserPerson' in value):
            return value['UserPerson']['id']

def get_active_accounts(data):
    accounts = []
    for value in data['Response']:
        if('MonetaryAccountBank' in value):
            item = value['MonetaryAccountBank']
            if('status' in item and item['status'] == 'ACTIVE'):
                accounts.append(item)
    return accounts

def generate_signature(string_to_sign: str, keys: RsaKey) -> str:
    bytes_to_sign = string_to_sign.encode()
    signer = PKCS1_v1_5.new(keys)
    digest = SHA256.new()
    digest.update(bytes_to_sign)
    sign = signer.sign(digest)
    return b64encode(sign)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up bunq sensors."""
    keys = RSA.generate(2048)
    PRIVATE_KEY_CLIENT = keys.export_key(format='PEM', passphrase=None, pkcs=8).decode('utf-8')
    PUBLIC_KEY_CLIENT = keys.publickey().export_key(format='PEM', passphrase=None, pkcs=8).decode('utf-8')
    REQUEST_ID = get_id(20)

    sensors = []
    user_id = ''
    session_token = ''
    installation_token = ''

    try:
        # setup api context
        installation_response = requests.post(HOST + '/v1/installation', data = json.dumps({'client_public_key': PUBLIC_KEY_CLIENT}), headers = {'Content-Type': 'application/json', 'User-Agent': 'HomeAssistant', 'X-Bunq-Language': 'en_US', 'X-Bunq-Region': 'nl_NL', 'X-Bunq-Client-Request-Id': REQUEST_ID, 'X-Bunq-Geolocation': GEOLOCATION, 'X-Bunq-Client-Signature': ''})
        installation = installation_response.json()
        installation_token = get_token(installation)
    except requests.exceptions.HTTPError as http_error:
        _LOGGER.error('Error with installation api (http_error): %s', http_error)
        raise PlatformNotReady
    except requests.exceptions.ConnectionError as connection_error:
        _LOGGER.error('Error with installation api (connection_error): %s', connection_error)
        raise PlatformNotReady
    except requests.exceptions.Timeout as timeout_error:
        _LOGGER.error('Error with installation api (timeout_error): %s', timeout_error)
        raise PlatformNotReady
    except requests.exceptions.TooManyRedirects as too_many_redirects_error:
        _LOGGER.error('Error with installation api (too_many_redirects_error): %s', too_many_redirects_error)
        raise PlatformNotReady
    except requests.exceptions.RequestException as request_exception:
        _LOGGER.error('Error with installation api (request_exception): %s', request_exception)
        raise PlatformNotReady
    except Exception as exception:
        _LOGGER.error('Error with installation api (exception): %s - PUBLIC_KEY_CLIENT: %s - installation json: %s', sys.exc_info()[0], PUBLIC_KEY_CLIENT, installation)
        raise PlatformNotReady

    try:
        device_server_response = requests.post(HOST + '/v1/device-server', data = json.dumps({'description': 'Home Assistant', 'secret': config[CONF_API_KEY], 'permitted_ips': config[CONF_PERMITTED_IPS].split(',')}), headers = {'Content-Type': 'application/json', 'User-Agent': 'HomeAssistant', 'X-Bunq-Language': 'en_US', 'X-Bunq-Region': 'nl_NL', 'X-Bunq-Client-Request-Id': REQUEST_ID, 'X-Bunq-Geolocation': GEOLOCATION, 'X-Bunq-Client-Signature': '', 'X-Bunq-Client-Authentication': installation_token})
    except Exception as exception:
        _LOGGER.error('Error with device-server api: %s', sys.exc_info()[0])
        raise PlatformNotReady

    try:
        body = json.dumps({'secret': config[CONF_API_KEY]})
        signature = generate_signature(body, keys)
        session_server_response = requests.post(HOST + '/v1/session-server', data = body, headers = {'Content-Type': 'application/json', 'User-Agent': 'HomeAssistant', 'X-Bunq-Language': 'en_US', 'X-Bunq-Region': 'nl_NL', 'X-Bunq-Client-Request-Id': REQUEST_ID, 'X-Bunq-Geolocation': GEOLOCATION, 'X-Bunq-Client-Signature': signature, 'X-Bunq-Client-Authentication': installation_token})
        session_server = session_server_response.json()
        user_id = get_user_id(session_server)
        session_token = get_token(session_server)
    except Exception as exception:
        _LOGGER.error('Error with session-server api: %s - session_server : %s', sys.exc_info()[0], session_server)
        raise PlatformNotReady

    # create sensors
    try:
        for account in get_account_data(user_id, session_token):
            sensors.append(BunqBalanceSensor(account))
    except Exception as exception:
        _LOGGER.error('Error setting up sensor: %s', sys.exc_info()[0])
        raise PlatformNotReady

    async_add_entities(sensors, True)

    # schedule updates for sensors
    data = BunqData(hass, user_id, session_token, sensors)
    await data.schedule_update(UPDATE_INTERVAL)


def get_account_data(user_id, session_token):
    """Get active bunq accounts."""
    active_accounts = []
    response = requests.get(HOST + '/v1/user/' + str(user_id) + '/monetary-account', headers = {'Content-Type': 'application/json', 'User-Agent': 'HomeAssistant', 'X-Bunq-Language': 'en_US', 'X-Bunq-Region': 'nl_NL', 'X-Bunq-Client-Request-Id': REQUEST_ID, 'X-Bunq-Geolocation': GEOLOCATION, 'X-Bunq-Client-Signature': '', 'X-Bunq-Client-Authentication': session_token})
    accounts = response.json()
    return get_active_accounts(accounts)

class BunqBalanceSensor(Entity):
    """Setup bunq balance sensor."""

    def __init__(self, account):
        """Initialize the sensor."""
        self.id = account['id']
        self._name = account['description']
        self._state = float(account['balance']['value'])
        self._unit_of_measurement = account['currency']

    @property
    def name(self):
        """Return the name."""
        return self._name

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
        return ICON

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    def load_data(self, data):
        """Update sensor data."""
        old_balance = self._state
        self._state = data.get(self.id)
        return self._state == old_balance


class BunqData:
    """Get the latest data and updates the sensors."""

    def __init__(self, hass, user_id, session_token, sensors):
        """Initialize the data object."""
        self._user_id = user_id
        self._session_token = session_token
        self._sensors = sensors
        self.data = {}
        self.hass = hass

    async def update_devices(self):
        """Update all sensors."""
        tasks = []

        for sensor in self._sensors:
            if sensor.load_data(self.data):
                tasks.append(sensor.async_update_ha_state())
        if tasks:
            await asyncio.wait(tasks)

    async def schedule_update(self, update_interval):
        """Schedule an update."""
        async_track_time_interval(self.hass, self.async_update, update_interval)

    async def async_update(self, *_):
        """Update data."""
        try:
            # get new data from api
            accounts = get_account_data(self._user_id, self._session_token)
        except Exception as exception:
            _LOGGER.error('Error updating sensor: %s', exception)

        # create a dict with account id as key and account data as value
        self.data = {account['id']: float(account['balance']['value']) for account in accounts}

        # update the sensors
        await self.update_devices()