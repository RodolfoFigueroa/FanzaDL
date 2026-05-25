class RequestError(Exception):
    """Raised when a request returns an error."""


class AuthExpiredError(Exception):
    """Raised when the authentication has expired."""

    def __init__(self, message: str = "Authentication has expired") -> None:
        super().__init__(message)
