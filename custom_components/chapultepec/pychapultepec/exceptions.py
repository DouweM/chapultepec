"""Exceptions raised by pychapultepec."""

from __future__ import annotations


class ChapultepecError(Exception):
    """Base class for all pychapultepec errors."""


class ChapultepecConnectionError(ChapultepecError):
    """A network-level failure talking to the Attractions.io API."""


class ChapultepecRequestError(ChapultepecError):
    """The API returned an unexpected HTTP status.

    Carries the HTTP ``status`` and any response ``body`` for diagnostics.
    """

    def __init__(self, message: str, *, status: int | None = None, body: str | None = None) -> None:
        """Store the status code and response body alongside the message."""
        super().__init__(message)
        self.status = status
        self.body = body


class ChapultepecParseError(ChapultepecError):
    """A response or bundled record could not be parsed as expected."""
