"""Asset manifest helpers for video projects.

Every downloaded, generated, rendered, or data-derived asset should be recorded
next to the project in `asset_manifest.json`. Other helper scripts import this
module so assets share one audit trail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_NAME = "asset_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_env(path: Path | None = None) -> None:
    """Load root `.env` if python-dotenv is installed, with a tiny fallback."""
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        return
    except Exception:
        pass

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def manifest_path(project_dir: Path) -> Path:
    return project_dir.resolve() / MANIFEST_NAME


def load_manifest(project_dir: Path) -> dict[str, Any]:
    path = manifest_path(project_dir)
    if not path.exists():
        now = utc_now()
        return {
            "schema_version": 1,
            "created_at": now,
            "updated_at": now,
            "assets": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(project_dir: Path, manifest: dict[str, Any]) -> Path:
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = utc_now()
    path = manifest_path(project_dir)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def make_asset_id(entry: dict[str, Any]) -> str:
    parts = [
        str(entry.get("source_platform") or ""),
        str(entry.get("asset_id") or ""),
        str(entry.get("asset_title") or ""),
        str(entry.get("source_url") or ""),
        str(entry.get("download_url") or ""),
        str(entry.get("local_path") or ""),
        str(entry.get("prompt") or ""),
        utc_now(),
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"asset_{digest}"


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in entry.items():
        if value is None:
            continue
        if isinstance(value, Path):
            clean[key] = str(value)
        else:
            clean[key] = value

    clean.setdefault("manifest_id", make_asset_id(clean))
    clean.setdefault("added_at", utc_now())
    clean.setdefault("used_in_timeline", False)
    return clean


def add_asset_entry(project_dir: Path, entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    manifest = load_manifest(project_dir)
    asset = normalize_entry(entry)

    assets = manifest.setdefault("assets", [])
    replace_index: int | None = None
    for idx, existing in enumerate(assets):
        same_manifest_id = existing.get("manifest_id") == asset.get("manifest_id")
        same_local_path = asset.get("local_path") and existing.get("local_path") == asset.get("local_path")
        same_external_id = (
            asset.get("source_platform")
            and asset.get("asset_id")
            and existing.get("source_platform") == asset.get("source_platform")
            and existing.get("asset_id") == asset.get("asset_id")
        )
        if same_manifest_id or same_local_path or same_external_id:
            replace_index = idx
            break

    if replace_index is None:
        assets.append(asset)
    else:
        merged = {**assets[replace_index], **asset}
        assets[replace_index] = merged
        asset = merged

    path = save_manifest(project_dir, manifest)
    return path, asset


def check_manifest(project_dir: Path) -> tuple[list[str], list[str]]:
    manifest = load_manifest(project_dir)
    errors: list[str] = []
    warnings: list[str] = []

    assets = manifest.get("assets", [])
    if not assets:
        warnings.append("manifest has no assets")
        return errors, warnings

    for idx, asset in enumerate(assets, start=1):
        label = asset.get("manifest_id") or f"asset #{idx}"
        if not asset.get("source_platform"):
            errors.append(f"{label}: missing source_platform")
        if not asset.get("local_path"):
            warnings.append(f"{label}: missing local_path")
        if not (asset.get("license_url") or asset.get("rights_statement") or asset.get("policy_or_license_notes")):
            warnings.append(f"{label}: missing license_url, rights_statement, or policy_or_license_notes")

        asset_type = str(asset.get("asset_type") or "")
        if asset_type.startswith("generated"):
            if not asset.get("prompt"):
                errors.append(f"{label}: generated asset missing prompt")
            if not (asset.get("model") or asset.get("generation_provider")):
                errors.append(f"{label}: generated asset missing model/generation_provider")
        if asset_type == "map" and not asset.get("attribution_text"):
            errors.append(f"{label}: map asset missing attribution_text")
        if asset_type == "chart" and not (asset.get("data_source") or asset.get("query_url")):
            errors.append(f"{label}: chart asset missing data_source/query_url")

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Create, inspect, and validate asset manifests.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Create asset_manifest.json if missing.")
    init_parser.add_argument("project_dir", type=Path)

    list_parser = sub.add_parser("list", help="Print manifest assets as JSON.")
    list_parser.add_argument("project_dir", type=Path)

    check_parser = sub.add_parser("check", help="Validate required manifest fields.")
    check_parser.add_argument("project_dir", type=Path)

    add_parser = sub.add_parser("add", help="Add an asset from a JSON object.")
    add_parser.add_argument("project_dir", type=Path)
    add_parser.add_argument("--entry-json", required=True, help="JSON object for the asset entry.")

    args = parser.parse_args()

    if args.command == "init":
        path = save_manifest(args.project_dir, load_manifest(args.project_dir))
        print(path)
    elif args.command == "list":
        print(json.dumps(load_manifest(args.project_dir), indent=2, ensure_ascii=False))
    elif args.command == "check":
        errors, warnings = check_manifest(args.project_dir)
        for warning in warnings:
            print(f"warning: {warning}")
        for error in errors:
            print(f"error: {error}")
        raise SystemExit(1 if errors else 0)
    elif args.command == "add":
        entry = json.loads(args.entry_json)
        path, asset = add_asset_entry(args.project_dir, entry)
        print(json.dumps({"manifest": str(path), "asset": asset}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
