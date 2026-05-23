class RequestError(Exception):
    """Base class for exceptions in this module."""


class AuthExpiredError(Exception):
    """Raised when the authentication token has expired."""
