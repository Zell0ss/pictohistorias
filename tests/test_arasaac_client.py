import httpx
import pytest

from lib.arasaac_client import fetch_all_pictograms


class FakeResponse:
    def __init__(self, data, status_ok=True):
        self._data = data
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._data


def test_fetch_all_pictograms_builds_correct_url_and_returns_json(monkeypatch):
    fake_data = [{"_id": 1, "keywords": [{"keyword": "coche"}]}]
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse(fake_data)

    monkeypatch.setattr(httpx, "get", fake_get)

    result = fetch_all_pictograms("es", "https://api.arasaac.org/api")

    assert result == fake_data
    assert captured["url"] == "https://api.arasaac.org/api/pictograms/all/es"


def test_fetch_all_pictograms_raises_on_http_error(monkeypatch):
    def fake_get(url, timeout):
        return FakeResponse(None, status_ok=False)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        fetch_all_pictograms("es", "https://api.arasaac.org/api")
