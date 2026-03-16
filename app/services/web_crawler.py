import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set


DEFAULT_HEADERS = {
    "User-Agent": "NormativaSyncBot/1.0 (+internal ingestion service)"
}

def discover_links(
    base_url: str,
    allowed_domains: List[str],
    timeout: int = 15
) -> List[str]:
    """
    Descubre y devuelve URLs potencialmente documentales
    a partir de una página base.

    - Filtra por dominios permitidos
    - Elimina fragmentos (#)
    - Descarta enlaces no documentales
    - Devuelve URLs únicas
    """

    try:
        response = requests.get(
            base_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[discover_links] Error accediendo a {base_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    discovered: Set[str] = set()

    for tag in soup.find_all("a", href=True):
        raw_href = tag["href"].strip()

        # Ignorar anchors vacíos
        if not raw_href:
            continue

        # Normalizar a URL absoluta
        absolute_url = urljoin(base_url, raw_href)

        # Quitar fragmentos (#algo)
        absolute_url = absolute_url.split("#")[0]

        parsed = urlparse(absolute_url)

        # Validar dominio permitido
        if parsed.netloc not in allowed_domains:
            continue

        # Ignorar esquemas no HTTP
        if parsed.scheme not in ("http", "https"):
            continue

        lower_url = absolute_url.lower()

        # Filtrar extensiones irrelevantes
        if lower_url.endswith((
            ".jpg", ".jpeg", ".png", ".gif",
            ".svg", ".css", ".js",
            ".ico", ".zip", ".rar",
            ".mp4", ".mp3"
        )):
            continue

        # Ignorar mailto / tel
        if lower_url.startswith(("mailto:", "tel:")):
            continue

        discovered.add(absolute_url)

    print(f"[discover_links] {len(discovered)} URLs descubiertas desde {base_url}")

    return sorted(discovered)
