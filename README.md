[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Bunq Integration

This integration provides monetary account balance sensors for Bunq

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

Simply follow the config flow.
The integration uses oauth.
In order to get the "client id" and the "client secret" follow these steps:

-   Open the bunq app
-   Go to "Profile"
-   Go to "Developers"
-   Click OAuth
-   Click "Add redirect URL"
-   Enter "https://my.home-assistant.io/redirect/oauth/"
-   Click "Done"
-   Click "SHOW CLIENT DETAILS"
-   use the values when configuring the integration

Note:
During the configuration process you will be redirected to `https://my.home-assistant.io`.
There, you need to enter the address on which your home assistant can be reached (it can be local ip/dns or external one)
Then click on "Link Account"

## Why oauth instead of API Key ?

oauth is much safer. API keys gives all writes to your accounts (including money transfert).
However, oauth only allow reading.

## Displaying transaction details

Each sensor can show the balance as well as a list of transactions.  
You can use the custom card [html-template-card](https://github.com/piotrmachowski/home-assistant-lovelace-html-jinja2-template-card) to display them.

Example of configuration:

```yaml
type: "custom:html-template-card"
title: Transactions
ignore_line_breaks: true
content: >
    <style>.bunq_table { width:100% } .bunq_table tr:nth-child(even) {background:
    var(--material-secondary-background-color)}</style> <table class="bunq_table">
    <tr> <th >Amount</th> <th>Description</th> <th>Time</th> </tr> {% for
    transaction in state_attr('sensor.bunq_groceries', 'transactions') %}

    <tr>

    <td style="width: 20%;text-align:right">

    {{ transaction.amount }}&nbsp;{{ transaction.currency }}

    </td>

    <td style="padding:0 0.5em">

    {{ transaction.description }}

    </td>

    <td style="width: 20%;">

    {% set created = as_timestamp(now()) - (strptime(transaction.created,
    '%Y-%m-%d %H:%M:%S.%f') + now().utcoffset()).timestamp() %}

    {% set days = (created // (60 * 60 * 24)) | int %}

    {% set weeks = (days // 7) | int %}

    {% set hours = (created // (60 * 60)) | int %}

    {% set hours =  hours - days * 24 %}

    {% set minutes = (created // 60) | int %}

    {% set minutes = minutes - (days * 24 * 60) - (hours * 60) %}

    {% set days = (days | int) - (weeks * 7) %}

    {% macro phrase(value, name) %}

    {%- set value = value | int %}

    {{- '{}{}'.format(value, name) if value | int > 0 else '' }}

    {%- endmacro %}

    {% set text = [ phrase(weeks, 'w'), phrase(days, 'd'), phrase(hours, 'h'),
    phrase(minutes, 'm') ] | select('!=','') | list | join(', ') %}

    {% set last_comma = text.rfind(',') %}

    {% set text = text[:last_comma] + text[last_comma + 1:] %} {{text}} </td>

    </tr>

    {% endfor %}

    </table>
```

## CHANGELOG

#### V2.0.0

-   Replace api_key by oauth
-   Modernize all the code

#### V1.0.0

-   Initial version
