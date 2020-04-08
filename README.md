[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)  

# Bunq Integration

This integration provides monetary account balance sensors for Bunq

## Sensor configuration

```
- platform: bunq
  api_key: "<BUNQ_API_SECRET_KEY>"
  permitted_ips: "<PERMITTED_IPS>"
```

Where:
- `<BUNQ_API_SECRET_KEY>` must be replace by the API KEY provided by bunq
- `<PERMITTED_IPS>` is a list (comma separated, no spaces) of IP addresses allowed to reach the IP  
   for instance: `1.1.1.1,8.8.8.8`  
   You can use `*` to allow any IP (that comes with a security trad-off)