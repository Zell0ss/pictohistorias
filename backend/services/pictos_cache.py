from pathlib import Path

import httpx


def ensure_picto_png_cached(
    picto_id: int, static_base: str, cache_dir: str = "cache/pictos", timeout: float = 5.0
) -> bool:
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    png_path = cache_path / f"{picto_id}_300.png"
    if png_path.exists():
        return True

    url = f"{static_base}/pictograms/{picto_id}/{picto_id}_300.png"
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError:
        return False

    png_path.write_bytes(response.content)
    return True
