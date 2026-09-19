import httpx


def fetch_all_pictograms(locale: str, base_url: str, timeout: float = 60.0) -> list[dict]:
    url = f"{base_url}/pictograms/all/{locale}"
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
