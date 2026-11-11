"""
tests/helpers/network_guard.py - Hermetic Network Guard & Mock Response Utilities.
Provides exception classes, mock response wrappers, and verification helpers
ensuring 100% network isolation during test suite execution.
"""

from typing import Dict, Any, Optional
import json
import requests


class HermeticNetworkViolation(Exception):
    """Raised when an unmocked outbound network connection is attempted in hermetic mode."""
    pass


class MockResponse:
    """Universal mock for requests.Response."""

    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        content: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        url: str = ""
    ):
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}

        if json_data is not None:
            self._content = json.dumps(json_data, ensure_ascii=False).encode("utf-8")
            self.headers.setdefault("Content-Type", "application/json")
        elif content is not None:
            self._content = content
        else:
            self._content = text.encode("utf-8")

        self.text = self._content.decode("utf-8", errors="replace")
        self.ok = 200 <= status_code < 300

    @property
    def content(self) -> bytes:
        return self._content

    def json(self) -> Any:
        return json.loads(self._content.decode("utf-8"))

    def raise_for_status(self):
        if not self.ok:
            http_err = requests.HTTPError(
                f"HTTP {self.status_code} Error for URL: {self.url}",
                response=self
            )
            raise http_err

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockUrllibResponse:
    """Universal mock for urllib.request.urlopen context manager."""

    def __init__(
        self,
        data: bytes = b"",
        status: int = 200,
        headers: Optional[Dict[str, str]] = None
    ):
        self._data = data
        self.status = status
        self.code = status
        self.headers = headers or {}

    def read(self, *args, **kwargs) -> bytes:
        return self._data

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
