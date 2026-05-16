import socket

import requests as stdlib_requests


class _TimeoutSession(stdlib_requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", 30)
        return super().request(*args, **kwargs)


class NetworkManager:
    def __init__(self, config):
        self._config = config
        self._session = _TimeoutSession()

    @property
    def session(self):
        return self._session

    @property
    def is_connected(self):
        try:
            socket.setdefaulttimeout(3)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("8.8.8.8", 53))
            return True
        except OSError:
            return False

    @property
    def ip_address(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "offline"

    def connect(self, retries=4):
        if not self.is_connected:
            raise RuntimeError("No network connection available")
