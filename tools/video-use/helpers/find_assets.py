"""Search and optionally download assets from agent-friendly sources.

Default behavior uses direct/no-key public sources. If root `.env` contains
free API keys, pass `--include-keyed` to include keyed sources too.

Examples:
    python tools/video-use/helpers/find_assets.py "moon landing" --media-type video
    python tools/video-use/helpers/find_assets.py "camera click" --media-type audio --include-keyed
    python tools/video-use/helpers/find_assets.py "map pin" --media-type icon --download 0 --project-dir edit/demo
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from asset_manifest import add_asset_entry, load_env, utc_now


USER_AGENT = "video-editing-asset-agent/0.1"
TIMEOUT = 30


def freesound_api_key() -> str:
    """Freesound labels the client secret as "Client secret / API key"."""
    return os.environ.get("FREESOUND_CLIENT_SECRET") or os.environ.get("FREESOUND_API_KEY", "")


def freesound_access_token() -> str:
    return os.environ.get("FREESOUND_ACCESS_TOKEN", "")


def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    response = requests.get(url, params=params, headers=request_headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def media_matches(requested: str, *allowed: str) -> bool:
    return requested == "all" or requested in allowed


def clean_filename(value: str, fallback: str = "asset") -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return stem[:100] or fallback


def extension_from_response(response: requests.Response, fallback_url: str) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    ext = mimetypes.guess_extension(content_type) if content_type else None
    if ext:
        return ext
    path_ext = Path(urlparse(fallback_url).path).suffix
    return path_ext or ".bin"


def normalize_result(**kwargs: Any) -> dict[str, Any]:
    result = {
        "source_platform": kwargs.get("source_platform"),
        "asset_type": kwargs.get("asset_type"),
        "asset_id": kwargs.get("asset_id"),
        "asset_title": kwargs.get("asset_title"),
        "creator": kwargs.get("creator"),
        "source_url": kwargs.get("source_url"),
        "download_url": kwargs.get("download_url"),
        "thumbnail_url": kwargs.get("thumbnail_url"),
        "license_name": kwargs.get("license_name"),
        "license_url": kwargs.get("license_url"),
        "rights_statement": kwargs.get("rights_statement"),
        "allowed_use": kwargs.get("allowed_use"),
        "restrictions": kwargs.get("restrictions"),
        "metadata": kwargs.get("metadata") or {},
    }
    return {key: value for key, value in result.items() if value not in (None, "", [])}


def search_openverse(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if media_matches(media_type, "image"):
        data = get_json(
            "https://api.openverse.engineering/v1/images/",
            {"q": query, "page_size": limit},
        )
        for item in data.get("results", []):
            results.append(normalize_result(
                source_platform="openverse",
                asset_type="image",
                asset_id=item.get("id"),
                asset_title=item.get("title"),
                creator=item.get("creator"),
                source_url=item.get("foreign_landing_url"),
                download_url=item.get("url"),
                thumbnail_url=item.get("thumbnail"),
                license_name=item.get("license"),
                license_url=item.get("license_url"),
                allowed_use="Verify source page license before final use.",
                metadata={"provider": item.get("source")},
            ))
    if media_matches(media_type, "audio", "sfx", "music"):
        data = get_json(
            "https://api.openverse.engineering/v1/audio/",
            {"q": query, "page_size": limit},
        )
        for item in data.get("results", []):
            results.append(normalize_result(
                source_platform="openverse",
                asset_type="audio",
                asset_id=item.get("id"),
                asset_title=item.get("title"),
                creator=item.get("creator"),
                source_url=item.get("foreign_landing_url"),
                download_url=item.get("url"),
                thumbnail_url=item.get("thumbnail"),
                license_name=item.get("license"),
                license_url=item.get("license_url"),
                allowed_use="Verify source page license before final use.",
                metadata={"provider": item.get("source")},
            ))
    return results[:limit]


def search_nasa(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    nasa_type = None if media_type == "all" else {
        "image": "image",
        "video": "video",
        "audio": "audio",
        "sfx": "audio",
        "music": "audio",
    }.get(media_type)
    params: dict[str, Any] = {"q": query, "page_size": limit}
    if nasa_type:
        params["media_type"] = nasa_type

    data = get_json("https://images-api.nasa.gov/search", params)
    results: list[dict[str, Any]] = []
    for item in data.get("collection", {}).get("items", []):
        record = (item.get("data") or [{}])[0]
        links = item.get("links") or []
        nasa_id = record.get("nasa_id")
        results.append(normalize_result(
            source_platform="nasa",
            asset_type=record.get("media_type"),
            asset_id=nasa_id,
            asset_title=record.get("title"),
            creator="NASA",
            source_url=f"https://images.nasa.gov/details/{nasa_id}" if nasa_id else None,
            thumbnail_url=links[0].get("href") if links else None,
            license_name="NASA media usage guidelines",
            license_url="https://www.nasa.gov/nasa-brand-center/images-and-media/",
            rights_statement="Do not imply NASA endorsement; check item context and logo/people restrictions.",
            metadata={"api_href": item.get("href"), "date_created": record.get("date_created")},
        ))
    return results[:limit]


def search_met(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    if not media_matches(media_type, "image"):
        return []
    data = get_json(
        "https://collectionapi.metmuseum.org/public/collection/v1/search",
        {"q": query, "hasImages": "true"},
    )
    results: list[dict[str, Any]] = []
    for object_id in (data.get("objectIDs") or [])[:limit]:
        item = get_json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}")
        if not item.get("primaryImage"):
            continue
        results.append(normalize_result(
            source_platform="met",
            asset_type="image",
            asset_id=str(object_id),
            asset_title=item.get("title"),
            creator=item.get("artistDisplayName"),
            source_url=item.get("objectURL"),
            download_url=item.get("primaryImage"),
            thumbnail_url=item.get("primaryImageSmall"),
            license_name="Public Domain where open access applies",
            license_url="https://metmuseum.github.io/",
            rights_statement=item.get("rightsAndReproduction"),
            metadata={"object_date": item.get("objectDate"), "culture": item.get("culture")},
        ))
    return results[:limit]


def search_loc(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    params = {"fo": "json", "q": query, "c": limit}
    data = get_json("https://www.loc.gov/search/", params)
    results: list[dict[str, Any]] = []
    for item in data.get("results", [])[:limit]:
        image_urls = item.get("image_url") or []
        download_url = image_urls[-1] if image_urls else None
        original_format = ", ".join(item.get("original_format") or [])
        asset_type = "image"
        if "sound" in original_format.lower() or "audio" in original_format.lower():
            asset_type = "audio"
        elif "film" in original_format.lower() or "video" in original_format.lower():
            asset_type = "video"
        if not media_matches(media_type, asset_type) and not (
            media_type in {"sfx", "music"} and asset_type == "audio"
        ):
            continue
        results.append(normalize_result(
            source_platform="library_of_congress",
            asset_type=asset_type,
            asset_id=item.get("id") or item.get("number"),
            asset_title=item.get("title"),
            creator=", ".join(item.get("contributor") or []),
            source_url=item.get("url"),
            download_url=download_url,
            thumbnail_url=item.get("image_url", [None])[0] if item.get("image_url") else None,
            license_name=item.get("rights"),
            rights_statement=item.get("rights"),
            allowed_use="Check item rights metadata before final use.",
            metadata={"date": item.get("date"), "original_format": original_format},
        ))
    return results[:limit]


def search_internet_archive(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    media_filter = {
        "video": "movies",
        "audio": "audio",
        "sfx": "audio",
        "music": "audio",
        "image": "image",
    }.get(media_type)
    q = query
    if media_filter:
        q = f"({query}) AND mediatype:{media_filter}"
    data = get_json(
        "https://archive.org/advancedsearch.php",
        {
            "q": q,
            "fl[]": ["identifier", "title", "creator", "licenseurl", "mediatype", "collection"],
            "rows": limit,
            "page": 1,
            "output": "json",
        },
    )
    results: list[dict[str, Any]] = []
    for item in data.get("response", {}).get("docs", []):
        identifier = item.get("identifier")
        mediatype = item.get("mediatype")
        asset_type = "video" if mediatype == "movies" else mediatype
        results.append(normalize_result(
            source_platform="internet_archive",
            asset_type=asset_type,
            asset_id=identifier,
            asset_title=item.get("title"),
            creator=item.get("creator"),
            source_url=f"https://archive.org/details/{identifier}" if identifier else None,
            license_url=item.get("licenseurl"),
            allowed_use="Verify item metadata/license before final use.",
            metadata={"collection": item.get("collection"), "mediatype": mediatype},
        ))
    return results[:limit]


def search_wikimedia(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime",
        "format": "json",
    }
    data = get_json("https://commons.wikimedia.org/w/api.php", params)
    pages = data.get("query", {}).get("pages", {})
    results: list[dict[str, Any]] = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        ext = info.get("extmetadata") or {}
        mime = info.get("mime") or ""
        asset_type = "image"
        if mime.startswith("video/"):
            asset_type = "video"
        elif mime.startswith("audio/"):
            asset_type = "audio"
        if not media_matches(media_type, asset_type) and not (
            media_type in {"sfx", "music"} and asset_type == "audio"
        ):
            continue
        results.append(normalize_result(
            source_platform="wikimedia_commons",
            asset_type=asset_type,
            asset_id=str(page.get("pageid")),
            asset_title=page.get("title"),
            creator=(ext.get("Artist") or {}).get("value"),
            source_url=info.get("descriptionurl"),
            download_url=info.get("url"),
            thumbnail_url=info.get("thumburl"),
            license_name=(ext.get("LicenseShortName") or {}).get("value"),
            license_url=(ext.get("LicenseUrl") or {}).get("value"),
            rights_statement=(ext.get("UsageTerms") or {}).get("value"),
            metadata={"mime": mime, "description_url": info.get("descriptionurl")},
        ))
    return results[:limit]


def search_iconify(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    if not media_matches(media_type, "icon", "image"):
        return []
    data = get_json("https://api.iconify.design/search", {"query": query, "limit": limit})
    results: list[dict[str, Any]] = []
    for icon in data.get("icons", [])[:limit]:
        if ":" not in icon:
            continue
        prefix, name = icon.split(":", 1)
        results.append(normalize_result(
            source_platform="iconify",
            asset_type="icon",
            asset_id=icon,
            asset_title=icon,
            source_url=f"https://icon-sets.iconify.design/{prefix}/{name}/",
            download_url=f"https://api.iconify.design/{prefix}/{name}.svg",
            license_name="Varies by icon collection",
            license_url="https://iconify.design/docs/icons/license.html",
            allowed_use="Check collection license before final use.",
            metadata={"icon_collection": prefix, "icon_name": name},
        ))
    return results[:limit]


def search_natural_earth(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    if not media_matches(media_type, "map", "image"):
        return []
    datasets = [
        ("countries-110m", "Admin 0 countries, 110m scale", "110m_cultural/ne_110m_admin_0_countries.zip"),
        ("countries-50m", "Admin 0 countries, 50m scale", "50m_cultural/ne_50m_admin_0_countries.zip"),
        ("countries-10m", "Admin 0 countries, 10m scale", "10m_cultural/ne_10m_admin_0_countries.zip"),
        ("populated-places-110m", "Populated places, 110m scale", "110m_cultural/ne_110m_populated_places.zip"),
        ("rivers-110m", "Rivers and lake centerlines, 110m scale", "110m_physical/ne_110m_rivers_lake_centerlines.zip"),
        ("lakes-110m", "Lakes, 110m scale", "110m_physical/ne_110m_lakes.zip"),
    ]
    query_lower = query.lower()
    matches = [item for item in datasets if query_lower in item[0] or query_lower in item[1].lower()]
    if not matches:
        matches = datasets
    results = []
    for dataset_id, title, path in matches[:limit]:
        results.append(normalize_result(
            source_platform="natural_earth",
            asset_type="map_data",
            asset_id=dataset_id,
            asset_title=title,
            source_url="https://www.naturalearthdata.com/downloads/",
            download_url=f"https://naturalearth.s3.amazonaws.com/{path}",
            license_name="Public domain",
            license_url="https://www.naturalearthdata.com/about/terms-of-use/",
            allowed_use="Public domain base map data.",
        ))
    return results


def search_pexels(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    headers = {"Authorization": key}
    results: list[dict[str, Any]] = []
    if media_matches(media_type, "image"):
        data = get_json("https://api.pexels.com/v1/search", {"query": query, "per_page": limit}, headers)
        for item in data.get("photos", []):
            src = item.get("src") or {}
            results.append(normalize_result(
                source_platform="pexels",
                asset_type="image",
                asset_id=str(item.get("id")),
                asset_title=item.get("alt") or f"Pexels photo {item.get('id')}",
                creator=item.get("photographer"),
                source_url=item.get("url"),
                download_url=src.get("original") or src.get("large2x") or src.get("large"),
                thumbnail_url=src.get("small"),
                license_name="Pexels License",
                license_url="https://www.pexels.com/license/",
            ))
    if media_matches(media_type, "video"):
        data = get_json("https://api.pexels.com/videos/search", {"query": query, "per_page": limit}, headers)
        for item in data.get("videos", []):
            files = sorted(item.get("video_files") or [], key=lambda f: f.get("width") or 0, reverse=True)
            results.append(normalize_result(
                source_platform="pexels",
                asset_type="video",
                asset_id=str(item.get("id")),
                asset_title=f"Pexels video {item.get('id')}",
                creator=(item.get("user") or {}).get("name"),
                source_url=item.get("url"),
                download_url=files[0].get("link") if files else None,
                thumbnail_url=item.get("image"),
                license_name="Pexels License",
                license_url="https://www.pexels.com/license/",
            ))
    return results[:limit]


def search_pixabay(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    results: list[dict[str, Any]] = []
    if media_matches(media_type, "image"):
        data = get_json("https://pixabay.com/api/", {"key": key, "q": query, "per_page": limit, "safesearch": "true"})
        for item in data.get("hits", []):
            results.append(normalize_result(
                source_platform="pixabay",
                asset_type="image",
                asset_id=str(item.get("id")),
                asset_title=item.get("tags"),
                creator=item.get("user"),
                source_url=item.get("pageURL"),
                download_url=item.get("largeImageURL") or item.get("webformatURL"),
                thumbnail_url=item.get("previewURL"),
                license_name="Pixabay Content License",
                license_url="https://pixabay.com/service/license-summary/",
            ))
    if media_matches(media_type, "video"):
        data = get_json("https://pixabay.com/api/videos/", {"key": key, "q": query, "per_page": limit, "safesearch": "true"})
        for item in data.get("hits", []):
            videos = item.get("videos") or {}
            best = videos.get("large") or videos.get("medium") or videos.get("small") or {}
            results.append(normalize_result(
                source_platform="pixabay",
                asset_type="video",
                asset_id=str(item.get("id")),
                asset_title=item.get("tags"),
                creator=item.get("user"),
                source_url=item.get("pageURL"),
                download_url=best.get("url"),
                thumbnail_url=item.get("picture_id"),
                license_name="Pixabay Content License",
                license_url="https://pixabay.com/service/license-summary/",
            ))
    return results[:limit]


def search_unsplash(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key or not media_matches(media_type, "image"):
        return []
    data = get_json(
        "https://api.unsplash.com/search/photos",
        {"query": query, "per_page": limit},
        {"Authorization": f"Client-ID {key}"},
    )
    results: list[dict[str, Any]] = []
    for item in data.get("results", []):
        urls = item.get("urls") or {}
        user = item.get("user") or {}
        results.append(normalize_result(
            source_platform="unsplash",
            asset_type="image",
            asset_id=item.get("id"),
            asset_title=item.get("description") or item.get("alt_description"),
            creator=user.get("name"),
            source_url=item.get("links", {}).get("html"),
            download_url=urls.get("raw") or urls.get("full"),
            thumbnail_url=urls.get("small"),
            license_name="Unsplash License",
            license_url="https://unsplash.com/license",
            metadata={"download_location": item.get("links", {}).get("download_location")},
        ))
    return results[:limit]


def search_freesound(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = freesound_api_key()
    if not key or not media_matches(media_type, "audio", "sfx", "music"):
        return []
    data = get_json(
        "https://freesound.org/apiv2/search/",
        {"query": query, "page_size": limit, "fields": "id,name,url,username,license,previews,type,duration"},
        {"Authorization": f"Token {key}"},
    )
    results: list[dict[str, Any]] = []
    for item in data.get("results", []):
        previews = item.get("previews") or {}
        results.append(normalize_result(
            source_platform="freesound",
            asset_type="audio",
            asset_id=str(item.get("id")),
            asset_title=item.get("name"),
            creator=item.get("username"),
            source_url=item.get("url"),
            download_url=previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3"),
            license_name=item.get("license"),
            license_url=item.get("license"),
            allowed_use="Preview download by default. Use --freesound-original with OAuth access token for original quality.",
            metadata={
                "type": item.get("type"),
                "duration": item.get("duration"),
                "preview_download": True,
                "original_download_endpoint": f"https://freesound.org/apiv2/sounds/{item.get('id')}/download/",
            },
        ))
    return results[:limit]


def search_smithsonian(query: str, media_type: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("SMITHSONIAN_API_KEY")
    if not key:
        return []
    data = get_json("https://api.si.edu/openaccess/api/v1.0/search", {"q": query, "rows": limit, "api_key": key})
    results: list[dict[str, Any]] = []
    for row in data.get("response", {}).get("rows", [])[:limit]:
        content = row.get("content") or {}
        descriptive = content.get("descriptiveNonRepeating") or {}
        online_media = descriptive.get("online_media") or {}
        media = (online_media.get("media") or [{}])[0]
        download_url = media.get("content") or media.get("thumbnail")
        results.append(normalize_result(
            source_platform="smithsonian",
            asset_type="image",
            asset_id=row.get("id"),
            asset_title=descriptive.get("title") or row.get("title"),
            creator=descriptive.get("data_source"),
            source_url=descriptive.get("record_link"),
            download_url=download_url,
            thumbnail_url=media.get("thumbnail"),
            license_name="Smithsonian Open Access / item rights",
            license_url="https://www.si.edu/openaccess",
            allowed_use="Check item record rights before final use.",
        ))
    return results[:limit]


SEARCHERS: dict[str, Callable[[str, str, int], list[dict[str, Any]]]] = {
    "openverse": search_openverse,
    "nasa": search_nasa,
    "met": search_met,
    "library_of_congress": search_loc,
    "internet_archive": search_internet_archive,
    "wikimedia": search_wikimedia,
    "iconify": search_iconify,
    "natural_earth": search_natural_earth,
    "pexels": search_pexels,
    "pixabay": search_pixabay,
    "unsplash": search_unsplash,
    "freesound": search_freesound,
    "smithsonian": search_smithsonian,
}

DIRECT_SOURCES = [
    "openverse",
    "nasa",
    "met",
    "library_of_congress",
    "internet_archive",
    "wikimedia",
    "iconify",
    "natural_earth",
]

KEYED_SOURCES = ["pexels", "pixabay", "unsplash", "freesound", "smithsonian"]


def resolve_nasa_download(result: dict[str, Any]) -> str | None:
    api_href = (result.get("metadata") or {}).get("api_href")
    if not api_href:
        return None
    files = get_json(api_href)
    preferred_exts = (".mp4", ".mov", ".m4v", ".mp3", ".wav", ".jpg", ".jpeg", ".png", ".tif", ".tiff")
    for ext in preferred_exts:
        for file_url in files:
            if str(file_url).lower().endswith(ext):
                return file_url
    return files[0] if files else None


def resolve_internet_archive_download(result: dict[str, Any]) -> str | None:
    identifier = result.get("asset_id")
    if not identifier:
        return None
    data = get_json(f"https://archive.org/metadata/{identifier}")
    files = data.get("files") or []
    asset_type = result.get("asset_type")
    preferred_exts = {
        "video": (".mp4", ".mov", ".m4v", ".webm"),
        "audio": (".mp3", ".wav", ".flac", ".ogg"),
        "image": (".jpg", ".jpeg", ".png", ".tif", ".tiff"),
    }.get(asset_type, (".mp4", ".mp3", ".jpg", ".png"))
    for ext in preferred_exts:
        for file_info in files:
            name = file_info.get("name") or ""
            if name.lower().endswith(ext):
                return f"https://archive.org/download/{identifier}/{name}"
    return None


def resolve_download_url(result: dict[str, Any], prefer_freesound_original: bool = False) -> str | None:
    if result.get("source_platform") == "freesound" and prefer_freesound_original:
        if freesound_access_token() and result.get("asset_id"):
            return f"https://freesound.org/apiv2/sounds/{result['asset_id']}/download/"
        print("warning: FREESOUND_ACCESS_TOKEN missing; falling back to preview download", file=sys.stderr)
    if result.get("download_url"):
        return result["download_url"]
    if result.get("source_platform") == "nasa":
        return resolve_nasa_download(result)
    if result.get("source_platform") == "internet_archive":
        return resolve_internet_archive_download(result)
    return None


def download_asset(
    result: dict[str, Any],
    project_dir: Path,
    subdir: str = "assets",
    prefer_freesound_original: bool = False,
) -> tuple[Path, dict[str, Any]]:
    url = resolve_download_url(result, prefer_freesound_original)
    if not url:
        raise RuntimeError(f"no downloadable URL found for {result.get('asset_title') or result.get('asset_id')}")

    headers = {"User-Agent": USER_AGENT}
    original_freesound = result.get("source_platform") == "freesound" and "/download/" in url
    if original_freesound:
        headers["Authorization"] = f"Bearer {freesound_access_token()}"
    response = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
    response.raise_for_status()

    asset_type = result.get("asset_type") or "asset"
    out_dir = project_dir.resolve() / subdir / str(asset_type)
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = extension_from_response(response, url)
    title = result.get("asset_title") or result.get("asset_id") or "asset"
    filename = clean_filename(title, "asset")
    if not filename.lower().endswith(ext.lower()):
        filename += ext
    out_path = out_dir / filename

    counter = 2
    while out_path.exists():
        out_path = out_dir / f"{Path(filename).stem}-{counter}{ext}"
        counter += 1

    with out_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)

    metadata = dict(result.get("metadata") or {})
    metadata["download_kind"] = "original" if original_freesound else metadata.get("download_kind", "preview")
    entry = {**result, "download_url": url, "local_path": str(out_path), "downloaded_at": utc_now(), "metadata": metadata}
    manifest_path, asset = add_asset_entry(project_dir, entry)
    return manifest_path, asset


def run_search(args: argparse.Namespace) -> list[dict[str, Any]]:
    sources = args.source or DIRECT_SOURCES
    if args.include_keyed and not args.source:
        sources = [*DIRECT_SOURCES, *KEYED_SOURCES]

    results: list[dict[str, Any]] = []
    for source in sources:
        searcher = SEARCHERS[source]
        try:
            source_results = searcher(args.query, args.media_type, args.limit)
        except Exception as exc:
            print(f"warning: {source} search failed: {exc}", file=sys.stderr)
            continue
        results.extend(source_results)

    return results[: args.limit_total]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search agent-accessible asset sources.")
    parser.add_argument("query")
    parser.add_argument(
        "--media-type",
        default="all",
        choices=["all", "image", "video", "audio", "sfx", "music", "icon", "map"],
    )
    parser.add_argument("--source", action="append", choices=sorted(SEARCHERS), help="Restrict to one or more sources.")
    parser.add_argument("--include-keyed", action="store_true", help="Also query sources with keys present in root .env.")
    parser.add_argument("--limit", type=int, default=5, help="Per-source result limit.")
    parser.add_argument("--limit-total", type=int, default=20, help="Total result limit.")
    parser.add_argument("--output", type=Path, help="Optional JSON results file.")
    parser.add_argument("--download", type=int, help="Download result index from the search results.")
    parser.add_argument(
        "--freesound-original",
        action="store_true",
        help="Use OAuth original-quality Freesound download when downloading a Freesound result.",
    )
    parser.add_argument("--project-dir", type=Path, default=Path("."), help="Project folder for downloads and manifest.")
    parser.add_argument("--asset-subdir", default="assets", help="Download folder inside the project dir.")
    args = parser.parse_args()

    load_env()
    results = run_search(args)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.download is not None:
        if args.download < 0 or args.download >= len(results):
            raise SystemExit(f"--download index out of range; got {args.download}, have {len(results)} results")
        manifest_path, asset = download_asset(
            results[args.download],
            args.project_dir,
            args.asset_subdir,
            prefer_freesound_original=args.freesound_original,
        )
        print(json.dumps({"manifest": str(manifest_path), "downloaded": asset}, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
