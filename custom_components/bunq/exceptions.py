from json import dumps

"""Exceptions for the Bunq API."""


class BunqApiError(Exception):
    """Generic BunqApi exception."""

    def get_message(self):
        """get the message of the first error in the bunq response"""
        if len(self.args) > 1:
            if "Error" in self.args[1]:
                errs = self.args[1]["Error"]
                if len(errs) > 0 and "error_description" in errs[0]:
                    return errs[0]["error_description"]
            return dumps(self.args[1])

        return dumps(self.args[0])


class BunqApiConnectionError(BunqApiError):
    """BunqApi connection exception."""


class BunqApiConnectionTimeoutError(BunqApiConnectionError):
    """BunqApi connection timeout exception."""


class BunqApiRateLimitError(BunqApiConnectionError):
    """BunqApi Rate Limit exception."""
