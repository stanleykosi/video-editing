"""Render map plates for video projects with attribution and manifest entries.

Examples:
    python tools/video-use/helpers/render_map.py --provider osm --center 6.5244 3.3792 --zoom 11 --marker 6.5244,3.3792,Lagos --project-dir edit/demo
    python tools/video-use/helpers/render_map.py --provider natural-earth --bounds=-10,35,35,60 --marker 48.8566,2.3522,Paris --output europe.png
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import requests

from asset_manifest import REPO_ROOT, add_asset_entry, utc_now


USER_AGENT = "video-editing-map-agent/0.1"
TILE_SIZE = 256
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
NATURAL_EARTH_GEOJSON = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)


def parse_size(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def parse_bounds(value: str) -> tuple[float, float, float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bounds must be min_lon,min_lat,max_lon,max_lat")
    return parts[0], parts[1], parts[2], parts[3]


def parse_marker(value: str) -> dict[str, Any]:
    parts = [part.strip() for part in value.split(",", 2)]
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("marker must be lat,lon[,label]")
    return {
        "lat": float(parts[0]),
        "lon": float(parts[1]),
        "label": parts[2] if len(parts) > 2 else "",
    }


def parse_route(value: str) -> list[tuple[float, float]]:
    points = []
    for raw_point in value.split(";"):
        lat, lon = [float(part.strip()) for part in raw_point.split(",", 1)]
        points.append((lat, lon))
    return points


def latlon_to_tile_float(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def fetch_tile(x: int, y: int, z: int, cache_dir: Path) -> Image.Image:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for OSM map rendering. Install project dependencies first."
        ) from exc

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / str(z) / str(x) / f"{y}.png"
    if path.exists():
        return Image.open(path).convert("RGB")

    path.parent.mkdir(parents=True, exist_ok=True)
    url = OSM_TILE_URL.format(z=z, x=x, y=y)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    path.write_bytes(response.content)
    return Image.open(path).convert("RGB")


def add_attribution(image: Image.Image, text: str) -> None:
    try:
        from PIL import ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for OSM map rendering. Install project dependencies first."
        ) from exc

    draw = ImageDraw.Draw(image, "RGBA")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(14, image.width // 90))
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    pad = 8
    width = bbox[2] - bbox[0] + pad * 2
    height = bbox[3] - bbox[1] + pad * 2
    x = image.width - width - 12
    y = image.height - height - 12
    draw.rectangle((x, y, x + width, y + height), fill=(255, 255, 255, 210))
    draw.text((x + pad, y + pad), text, fill=(20, 20, 20, 255), font=font)


def draw_marker(draw: ImageDraw.ImageDraw, x: float, y: float, label: str = "") -> None:
    try:
        from PIL import ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for OSM map rendering. Install project dependencies first."
        ) from exc

    radius = 10
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#e11d48", outline="white", width=3)
    if label:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        except Exception:
            font = ImageFont.load_default()
        draw.text((x + 14, y - 12), label, fill="black", stroke_width=3, stroke_fill="white", font=font)


def render_osm(args: argparse.Namespace, output: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for OSM map rendering. Install project dependencies first."
        ) from exc

    if not args.center:
        raise SystemExit("--provider osm requires --center LAT LON")
    width, height = parse_size(args.size)
    lat, lon = args.center
    zoom = args.zoom
    center_x, center_y = latlon_to_tile_float(lat, lon, zoom)
    center_px = center_x * TILE_SIZE
    center_py = center_y * TILE_SIZE

    min_px = center_px - width / 2
    max_px = center_px + width / 2
    min_py = center_py - height / 2
    max_py = center_py + height / 2

    min_tile_x = math.floor(min_px / TILE_SIZE)
    max_tile_x = math.floor(max_px / TILE_SIZE)
    min_tile_y = math.floor(min_py / TILE_SIZE)
    max_tile_y = math.floor(max_py / TILE_SIZE)
    tile_count = (max_tile_x - min_tile_x + 1) * (max_tile_y - min_tile_y + 1)
    if tile_count > args.max_tiles:
        raise SystemExit(f"refusing to fetch {tile_count} OSM tiles; raise --max-tiles deliberately if needed")

    cache_dir = REPO_ROOT / ".asset-cache" / "osm_tiles"
    stitched = Image.new(
        "RGB",
        ((max_tile_x - min_tile_x + 1) * TILE_SIZE, (max_tile_y - min_tile_y + 1) * TILE_SIZE),
    )
    for tx in range(min_tile_x, max_tile_x + 1):
        for ty in range(min_tile_y, max_tile_y + 1):
            tile = fetch_tile(tx, ty, zoom, cache_dir)
            stitched.paste(tile, ((tx - min_tile_x) * TILE_SIZE, (ty - min_tile_y) * TILE_SIZE))

    crop_left = int(min_px - min_tile_x * TILE_SIZE)
    crop_top = int(min_py - min_tile_y * TILE_SIZE)
    image = stitched.crop((crop_left, crop_top, crop_left + width, crop_top + height))
    draw = ImageDraw.Draw(image)

    def point_px(marker_lat: float, marker_lon: float) -> tuple[float, float]:
        x_tile, y_tile = latlon_to_tile_float(marker_lat, marker_lon, zoom)
        return x_tile * TILE_SIZE - min_px, y_tile * TILE_SIZE - min_py

    for route in args.route or []:
        pixels = [point_px(route_lat, route_lon) for route_lat, route_lon in route]
        if len(pixels) > 1:
            draw.line(pixels, fill="#2563eb", width=5, joint="curve")

    for marker in args.marker or []:
        x, y = point_px(marker["lat"], marker["lon"])
        draw_marker(draw, x, y, marker["label"])

    attribution = "© OpenStreetMap contributors"
    add_attribution(image, attribution)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return {
        "map_data_source": "OpenStreetMap",
        "tile_or_static_map_provider": "OpenStreetMap public tile server",
        "attribution_text": attribution,
        "bounds_or_places": {"center": args.center, "zoom": zoom},
        "style_or_renderer": "render_map.py osm tile stitch",
        "license_name": "OpenStreetMap data ODbL",
        "license_url": "https://www.openstreetmap.org/copyright",
        "policy_or_license_notes": "Uses public OSM tiles for light/draft rendering; respect tile usage policy.",
    }


def geojson_cache_path() -> Path:
    return REPO_ROOT / ".asset-cache" / "natural_earth" / "ne_110m_admin_0_countries.geojson"


def load_natural_earth() -> dict[str, Any]:
    path = geojson_cache_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(NATURAL_EARTH_GEOJSON, headers={"User-Agent": USER_AGENT}, timeout=60)
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def iter_polygons(geometry: dict[str, Any]) -> list[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        return geometry.get("coordinates", [])
    if geometry.get("type") == "MultiPolygon":
        polygons = []
        for polygon in geometry.get("coordinates", []):
            polygons.extend(polygon)
        return polygons
    return []


def ring_intersects_bounds(ring: list[list[float]], bounds: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bounds
    for lon, lat in ring:
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return True
    return False


def render_natural_earth(args: argparse.Namespace, output: Path) -> dict[str, Any]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for Natural Earth map rendering. Install project dependencies first."
        ) from exc

    width, height = parse_size(args.size)
    if args.bounds:
        bounds = args.bounds
    elif args.center:
        lat, lon = args.center
        span = args.span
        bounds = (lon - span / 2, lat - span / 2, lon + span / 2, lat + span / 2)
    else:
        bounds = (-180.0, -58.0, 180.0, 85.0)

    min_lon, min_lat, max_lon, max_lat = bounds
    data = load_natural_earth()
    fig = plt.figure(figsize=(width / 160, height / 160), dpi=160)
    ax = plt.axes()
    ax.set_facecolor("#dbeafe")
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    for feature in data.get("features", []):
        for ring in iter_polygons(feature.get("geometry") or {}):
            if not ring or not ring_intersects_bounds(ring, bounds):
                continue
            xs = [point[0] for point in ring]
            ys = [point[1] for point in ring]
            ax.fill(xs, ys, facecolor="#f8fafc", edgecolor="#64748b", linewidth=0.45)

    for route in args.route or []:
        lats = [point[0] for point in route]
        lons = [point[1] for point in route]
        ax.plot(lons, lats, color="#2563eb", linewidth=2.4)

    for marker in args.marker or []:
        ax.scatter([marker["lon"]], [marker["lat"]], s=90, color="#e11d48", edgecolors="white", linewidths=1.6, zorder=5)
        if marker["label"]:
            ax.text(marker["lon"], marker["lat"], f"  {marker['label']}", color="#111827", fontsize=9, weight="bold", va="center")

    attribution = "Natural Earth public domain"
    ax.text(
        0.99,
        0.02,
        attribution,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#111827",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 3},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return {
        "map_data_source": "Natural Earth",
        "tile_or_static_map_provider": "Natural Earth vector data",
        "attribution_text": attribution,
        "bounds_or_places": {"bounds": bounds},
        "style_or_renderer": "render_map.py natural-earth matplotlib",
        "license_name": "Public domain",
        "license_url": "https://www.naturalearthdata.com/about/terms-of-use/",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render attributed map plates.")
    parser.add_argument("--provider", default="natural-earth", choices=["natural-earth", "osm"])
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--center", nargs=2, type=float, metavar=("LAT", "LON"))
    parser.add_argument("--zoom", type=int, default=10)
    parser.add_argument("--bounds", type=parse_bounds, help="min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--span", type=float, default=30.0, help="Degree span when using natural-earth + center.")
    parser.add_argument("--marker", action="append", type=parse_marker, help="lat,lon[,label]")
    parser.add_argument("--route", action="append", type=parse_route, help="lat,lon;lat,lon;...")
    parser.add_argument("--title", default="map plate")
    parser.add_argument("--max-tiles", type=int, default=16)
    args = parser.parse_args()

    output = args.output or (args.project_dir / "assets" / "maps" / "map.png")
    output = output.resolve()

    if args.provider == "osm":
        metadata = render_osm(args, output)
        platform = "openstreetmap"
    else:
        metadata = render_natural_earth(args, output)
        platform = "natural_earth"

    entry = {
        "source_platform": platform,
        "asset_type": "map",
        "asset_id": output.stem,
        "asset_title": args.title,
        "source_url": metadata.get("license_url"),
        "local_path": str(output),
        "downloaded_at": utc_now(),
        **metadata,
    }
    manifest_path, asset = add_asset_entry(args.project_dir, entry)
    print(json.dumps({"manifest": str(manifest_path), "asset": asset}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
