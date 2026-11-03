"""Thin wrapper around waapi-client with explicit connection lifecycle."""
import logging

from waapi import WaapiClient, CannotConnectToWaapiException

logger = logging.getLogger(__name__)


class WaapiConnection:
    def __init__(self, url: str | None = None):
        self._url = url
        self._client: WaapiClient | None = None

    def set_url(self, url: str | None) -> None:
        """Server address for the next connect(); None uses the library default."""
        self._url = url

    def is_connected(self) -> bool:
        try:
            return self._client is not None and self._client.is_connected()
        except Exception:
            return False

    def connect(self) -> None:
        """Connect to Wwise. Raises CannotConnectToWaapiException when Wwise is not running."""
        if self.is_connected():
            return
        self._drop()
        self._client = WaapiClient(url=self._url, allow_exception=True)
        logger.info("Connected to WAAPI")

    def call(self, uri: str, args: dict | None = None, options: dict | None = None):
        if not self.is_connected():
            raise CannotConnectToWaapiException("Not connected to Wwise")
        if options is not None:
            result = self._client.call(uri, args or {}, options=options)
        else:
            result = self._client.call(uri, args or {})
        # Successful calls always return a dict; None means the connection died mid-call
        if result is None:
            raise CannotConnectToWaapiException("Connection to Wwise lost")
        return result

    def subscribe(self, uri: str, callback, options: dict | None = None):
        if not self.is_connected():
            raise CannotConnectToWaapiException("Not connected to Wwise")
        return self._client.subscribe(uri, callback, options or {})

    def disconnect(self) -> None:
        self._drop()

    def _drop(self) -> None:
        if self._client is not None:
            try:
                if self._client.is_connected():
                    self._client.disconnect()
            except Exception:
                logger.debug("Ignoring error while disconnecting", exc_info=True)
            self._client = None
