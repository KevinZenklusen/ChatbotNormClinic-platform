from urllib.parse import urlparse
from pathlib import Path
import mimetypes
import requests

def _guess_extension(content_type: str | None, url: str) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ext.lstrip(".")

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix
    return suffix.lstrip(".") if suffix else ""


def _load_from_http(url: str, extension: str | None) -> dict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type")
    if content_type:
        content_type = content_type.split(";")[0]

    if extension:
        content_type = mimetypes.types_map.get(f".{extension}", content_type)

    if not content_type:
        content_type, _ = mimetypes.guess_type(url)

    return {
        "bytes": response.content,
        "content_type": content_type or "application/octet-stream",
        "extension": extension or _guess_extension(content_type, url)
    }


def _load_from_file(path: str, extension: str | None) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(path)

    content = file_path.read_bytes()

    if extension:
        content_type = mimetypes.types_map.get(f".{extension}")
    else:
        content_type, _ = mimetypes.guess_type(file_path.name)

    return {
        "bytes": content,
        "content_type": content_type or "application/octet-stream",
        "extension": extension or file_path.suffix.lstrip(".")
    }



from supabase import create_client
import os

def _load_from_supabase(parsed, extension: str | None) -> dict:
    bucket = parsed.netloc
    path = parsed.path.lstrip("/")

    if not bucket or not path:
        raise ValueError("Invalid supabase URL. Expected supabase://<bucket>/<path>")

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"]
    )

    content = supabase.storage.from_(bucket).download(path)

    content_type, _ = mimetypes.guess_type(path)

    return {
        "bytes": content,
        "content_type": content_type or "application/octet-stream",
        "extension": extension or Path(path).suffix.lstrip(".")
    }



def load_resource(
    source_url: str,
    *,
    extension: str | None = None
) -> dict:
    parsed = urlparse(source_url)

    if parsed.scheme in ("http", "https"):
        return _load_from_http(source_url, extension)

    if parsed.scheme == "file":
        location = parsed.path or parsed.netloc
        return _load_from_file(location, extension)

    if parsed.scheme == "supabase":
        return _load_from_supabase(parsed, extension)

    raise ValueError(f"Unsupported source_url scheme: {parsed.scheme}")
