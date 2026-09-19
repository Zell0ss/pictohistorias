import httpx

from backend.services.pictos_cache import ensure_picto_png_cached


class FakeResponse:
    def __init__(self, content=b"fake-png-bytes", status_ok=True):
        self.content = content
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise httpx.HTTPStatusError("boom", request=None, response=None)


def test_ensure_picto_png_cached_returns_true_without_network_when_already_cached(tmp_path, monkeypatch):
    cache_dir = tmp_path / "pictos"
    cache_dir.mkdir()
    (cache_dir / "5_300.png").write_bytes(b"ya existe")

    def _fail_if_called(url, timeout):
        raise AssertionError("no deberia llamar a la red si ya esta cacheado")

    monkeypatch.setattr(httpx, "get", _fail_if_called)

    assert ensure_picto_png_cached(5, "https://static.arasaac.org", cache_dir=str(cache_dir)) is True


def test_ensure_picto_png_cached_downloads_and_writes_file(tmp_path, monkeypatch):
    cache_dir = tmp_path / "pictos"
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        return FakeResponse(content=b"contenido-real")

    monkeypatch.setattr(httpx, "get", fake_get)

    resultado = ensure_picto_png_cached(7, "https://static.arasaac.org", cache_dir=str(cache_dir))

    assert resultado is True
    assert captured["url"] == "https://static.arasaac.org/pictograms/7/7_300.png"
    assert (cache_dir / "7_300.png").read_bytes() == b"contenido-real"


def test_ensure_picto_png_cached_returns_false_on_http_error(tmp_path, monkeypatch):
    cache_dir = tmp_path / "pictos"

    def fake_get(url, timeout):
        return FakeResponse(status_ok=False)

    monkeypatch.setattr(httpx, "get", fake_get)

    resultado = ensure_picto_png_cached(9, "https://static.arasaac.org", cache_dir=str(cache_dir))

    assert resultado is False
    assert not (cache_dir / "9_300.png").exists()
