import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Optional

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_HEADERS = {
    "User-Agent": "NormativaSyncBot/1.0 (+internal ingestion service)"
}


def create_session() -> requests.Session:
    """
    Crea una sesión HTTP con retries automáticos.
    """
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def is_allowed_domain(netloc: str, allowed_domains: List[str]) -> bool:
    """
    Permite dominios y subdominios.
    """
    return any(netloc.endswith(domain) for domain in allowed_domains)


def discover_links(
    base_url: str,
    allowed_domains: List[str],
    timeout: int = 15,
    visited: Optional[Set[str]] = None,
    session: Optional[requests.Session] = None,
) -> List[str]:
    """
    Descubre y devuelve URLs potencialmente documentales
    a partir de una página base.

    - Filtra por dominios permitidos
    - Elimina fragmentos (#)
    - Descarta enlaces no documentales
    - Devuelve URLs únicas
    - Soporte de subdominios
    - Validación de Content-Type (solo HTML)
    - Normalización de URLs
    - Filtro de enlaces irrelevantes
    - Evita revisitar URLs (visited)
    - Soporte de retries con session
    """

    if visited is None:
        visited = set()

    if base_url in visited:
        return []

    visited.add(base_url)

    if session is None:
        session = create_session()

    try:
        response = session.get(
            base_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[discover_links] Error accediendo a {base_url}: {e}")
        return []

    content_type = response.headers.get("Content-Type", "")

    if "text/html" not in content_type:
        print(f"[discover_links] Contenido no HTML en {base_url}")
        return []
    
    #print("response")
    
    #print(response.text)

    soup = BeautifulSoup(response.text, "html.parser")

    discovered: Set[str] = set()

    for tag in soup.find_all("a", href=True):
        raw_href = tag["href"].strip()

        if not raw_href:
            continue

        # Ignorar mailto / tel
        if raw_href.startswith(("mailto:", "tel:")):
            continue

        if raw_href.startswith("blank:#"):
            raw_href = raw_href.replace("blank:#", "")

        # Normalizar a URL absoluta
        absolute_url = urljoin(base_url, raw_href)

        # Quitar fragmentos (#algo)
        absolute_url = absolute_url.split("#")[0]

        # Normalizar trailing slash
        absolute_url = absolute_url.rstrip("/")

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

        # Filtrar rutas no útiles típicas
        if any(x in lower_url for x in ["login", "signup", "register", "logout"]):
            continue

        discovered.add(absolute_url)

    print(f"[discover_links] {len(discovered)} URLs descubiertas desde {base_url}")

    return sorted(discovered)


from typing import List, Set
from urllib.parse import urlparse


def normalize_urls_normativa_PNGCAM(url: str) -> str:
    """
    Normaliza URLs de normativa obtenida desde PNGCAM:
    
    Casos:
    - Agrega /texto si falta
    - Elimina sufijos dinámicos (/texto2023.../...)
    """

    if "/normativa/nacional/" not in url:
        return url

    parts = url.split("/normativa/nacional/")
    base = parts[0] + "/normativa/nacional/"
    tail = parts[1]

    # Caso: ya tiene /texto pero con sufijo dinámico
    if "/texto" in tail:
        # Nos quedamos hasta '/texto'
        before_texto = tail.split("/texto")[0]
        return base + before_texto + "/texto"

    # Caso: no tiene /texto
    return base + tail.rstrip("/") + "/texto"


def is_valid_special_url(url: str) -> bool:
    """
    Aplica filtros específicos del dominio.
    """

    lower = url.lower()

    # excluir legisalud
    if "legisalud" in lower:
        return False

    return True


def is_relevant_url(url: str) -> bool:
    lower = url.lower()

    return (
        "/normativa/nacional/" in lower
        or "boletinoficial.gob.ar/detalleaviso" in lower
        or lower.endswith(".pdf")
    )


def get_urls_normativa_PNGCAM(
    base_url: str,
    allowed_domains: List[str],
    visited: Set[str] = None
) -> List[str]:

    raw_urls = discover_links(
        base_url=base_url,
        allowed_domains=allowed_domains,
        visited=visited
    )

    processed: Set[str] = set()

    for url in raw_urls:

        if not is_valid_special_url(url):
            continue

        if not is_relevant_url(url):
            continue

        parsed = urlparse(url)

        # Normalización específica
        normalized_url = url

        if "argentina.gob.ar" in parsed.netloc:
            normalized_url = normalize_urls_normativa_PNGCAM(url)

        processed.add(normalized_url)

    print(f"[get_normativa_urls] {len(processed)} URLs finales procesadas")

    return sorted(processed)