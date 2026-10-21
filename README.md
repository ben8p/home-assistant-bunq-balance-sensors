[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Bunq Integration

This integration provides access to Bunq:

- monetary account balance sensors including transactions
- debit- and creditcard sensors with a reference to the linked account
- a service to transfer funds to own accounts
- a service to link an account to a card.

# ⚠️⚠️⚠️⚠️⚠️ Backward incompatibility ⚠️⚠️⚠️⚠️⚠️

Version 1.0.0 of the integration was using `configuration.yaml` and bunq api key.
This is now fully deprecated. It won't work anymore.
It was replaced by oauth.

If you are upgrading, before installing version 2.0.0 you should:

-   uninstall the previous integration
-   and clean up the configuration.yaml

# Minimum version for HA

2023.6.1+

## Integration configuration

Simply follow the config flow. You can connect to bunq in two ways:

|              | OAuth                                                                        | API key                                                                                   |
| ------------ | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Pros         | Authorized through bunq, no key to copy around, access limited to your IP    | Keeps working when your IP address changes                                               |
| Cons         | bunq blocks access when your IP address changes, you must re-authorize       | Must allow all IP addresses; anyone holding the key can use it from anywhere              |
| Best for     | A static IP address                                                          | A dynamic IP address (most residential ISPs)                                              |

Neither method is read-only: according to bunq, OAuth tokens can by default also create payments and manage cards, and an API key has broad access too.

### OAuth

In order to get the "client id" and the "client secret" follow these steps:

-   Open the bunq app
-   Go to "Profile"
-   Go to "Developers"
-   Click OAuth
-   Click "Add redirect URL"
-   Enter "https://my.home-assistant.io/redirect/oauth"
-   Click "Done"
-   Click "SHOW CLIENT DETAILS"
-   use the values when configuring the integration

Note:
During the configuration process you will be redirected to `https://my.home-assistant.io`.
There, you need to enter the address on which your home assistant can be reached (it can be local ip/dns or external one)
Then click on "Link Account"

### API key

-   Open the bunq app
-   Go to "Settings" > "Developers" > "API keys" and click "Add an API key"
-   Open the menu of the new key and tap "Allow All IP Addresses"
-   Paste the key in the integration

### IP address changes

bunq only accepts requests from the IP address that was registered when you connected.
If it changes, bunq answers `User credentials are incorrect. Incorrect API key or IP address.`
and Home Assistant asks you to re-authenticate. If this happens regularly, use an API key that allows all IP addresses.

## Displaying transaction details

Each account sensor can show the balance as well as a list of transactions.  
You can use the custom card [html-template-card](https://github.com/piotrmachowski/home-assistant-lovelace-html-jinja2-template-card) to display them.

Example of configuration:

```yaml
type: "custom:html-template-card"
title: Transactions
ignore_line_breaks: true
content: >
    <style>.bunq_table { width:100% } .bunq_table tr:nth-child(even) {background:
    var(--material-secondary-background-color)}</style>
    <table class="bunq_table">
        <tr>
            <th>Amount</th> <th>Description</th> <th>Time</th>
        </tr>

        {% for transaction in state_attr('sensor.bunq_groceries', 'transactions') %}
        <tr>
            <td style="width: 20%;text-align:right">
            {{ transaction.amount }}&nbsp;{{ transaction.currency }}
            </td>

            <td style="padding:0 0.5em">
            {{ transaction.description }}
            </td>

            <td style="width: 20%;">
            {{ strptime(transaction.created, '%Y-%m-%d %H:%M:%S.%f') | relative_time }}
            </td>
        </tr>
        {% endfor %}
    </table>
```

## CHANGELOG

#### V2.2.0

-   Add API key authentication, as an alternative to oauth, for users whose IP address changes
-   Ask to re-authenticate when bunq rejects the credentials (e.g. after an IP address change)
-   Remove the "Allow dynamic IP address" option, bunq ignores the wildcard when sent through the API

#### V2.1.0

-   Add card sensor and service
-   Add transfer service

#### V2.0.0

-   Replace api_key by oauth
-   Modernize all the code

#### V1.0.0

-   Initial version
