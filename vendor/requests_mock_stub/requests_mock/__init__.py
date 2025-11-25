from __future__ import annotations

import requests


class _Response:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code


class Mocker:
    def __init__(self):
        self._registry = {}
        self._orig_get = requests.get

    def get(self, url: str, text: str = "", status_code: int = 200):
        self._registry[url] = _Response(text=text, status_code=status_code)

    def __enter__(self):
        def _fake_get(url, *args, **kwargs):
            resp = self._registry.get(url)
            if resp:
                return resp
            return _Response(status_code=404)

        requests.get = _fake_get
        return self

    def __exit__(self, exc_type, exc, tb):
        requests.get = self._orig_get
        return False
