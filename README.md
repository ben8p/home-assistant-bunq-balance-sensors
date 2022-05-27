[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)  

# Bunq Integration

This integration provides monetary account balance sensors for Bunq

# Minimum version for HA

2021.12.0+

## Sensor configuration

```
- platform: bunq
  api_key: "<BUNQ_API_SECRET_KEY>"
  permitted_ips: "<PERMITTED_IPS>"
```

Where:
- `<BUNQ_API_SECRET_KEY>` must be replace by the API KEY provided by bunq
- `<PERMITTED_IPS>` is a list (comma separated, no spaces) of IP addresses allowed to reach the API  
   for instance: `1.1.1.1,8.8.8.8`  
   You can use `*` to allow any IP (that comes with a security trad-off)

## Displaying transaction details
Each sensor can show the balance as well as a list of transactions.  
You can use the custom card [html-template-card](https://github.com/piotrmachowski/home-assistant-lovelace-html-jinja2-template-card) to display them.

Example of configuration:
```yaml
type: 'custom:html-template-card'
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
