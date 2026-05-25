class RequestError(Exception):
    """Raised when a request returns an error."""


class AuthExpiredError(Exception):
    """Raised when the authentication has expired."""

    def __init__(self, message: str = "Authentication has expired") -> None:
        super().__init__(message)


class MalformedEmailError(Exception):
    """Raised when the email is malformed."""

    def __init__(self, message: str = "Malformed email address") -> None:
        super().__init__(message)


class WrongCredentialsError(Exception):
    """Raised when the username or password is incorrect."""

    def __init__(self, message: str = "Wrong username/password") -> None:
        super().__init__(message)
