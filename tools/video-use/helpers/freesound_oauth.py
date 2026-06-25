"""Freesound OAuth utility for original-quality downloads.

Freesound gives each app a client ID and a "Client secret / API key". The client
secret can be used as the token-auth API key for search, while original-quality
downloads require OAuth access tokens.

Examples:
    python tools/video-use/helpers/freesound_oauth.py auth-url
    python tools/video-use/helpers/freesound_oauth.py exchange --code YOUR_CODE --write-env
    python tools/video-use/helpers/freesound_oauth.py refresh --write-env
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests

from asset_manifest import REPO_ROOT, load_env, utc_now


AUTHORIZE_URL = "https://freesound.org/apiv2/oauth2/authorize/"
ACCESS_TOKEN_URL = "https://freesound.org/apiv2/oauth2/access_token/"
DEFAULT_REDIRECT_URI = "http://freesound.org/home/app_permissions/permission_granted/"


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"{name} is missing in .env or environment")
    return value


def update_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" not in line or line.strip().startswith("#"):
            out.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in values:
            out.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in values.items():
        if key not in seen:
            out.append(f"{key}={value}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def auth_url(client_id: str, state: str) -> str:
    return f"{AUTHORIZE_URL}?{urlencode({'client_id': client_id, 'response_type': 'code', 'state': state})}"


def exchange_code(client_id: str, client_secret: str, code: str) -> dict[str, str]:
    response = requests.post(
        ACCESS_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise SystemExit(f"Freesound token exchange failed ({response.status_code}): {response.text[:500]}")
    return response.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict[str, str]:
    response = requests.post(
        ACCESS_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise SystemExit(f"Freesound token refresh failed ({response.status_code}): {response.text[:500]}")
    return response.json()


def token_env(token_data: dict[str, str]) -> dict[str, str]:
    values = {
        "FREESOUND_ACCESS_TOKEN": token_data.get("access_token", ""),
        "FREESOUND_REFRESH_TOKEN": token_data.get("refresh_token", ""),
    }
    if token_data.get("expires_in"):
        values["FREESOUND_TOKEN_EXPIRES_IN"] = str(token_data["expires_in"])
        values["FREESOUND_TOKEN_RECEIVED_AT"] = utc_now()
    return {key: value for key, value in values.items() if value}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/exchange Freesound OAuth tokens.")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth-url", help="Print the Freesound authorization URL.")
    auth.add_argument("--state", default=None)

    exchange = sub.add_parser("exchange", help="Exchange the redirected code for access/refresh tokens.")
    exchange.add_argument("--code", required=True)
    exchange.add_argument("--write-env", action="store_true")

    refresh = sub.add_parser("refresh", help="Refresh the Freesound access token.")
    refresh.add_argument("--write-env", action="store_true")

    args = parser.parse_args()
    load_env()

    client_id = require_env("FREESOUND_CLIENT_ID")
    client_secret = os.environ.get("FREESOUND_CLIENT_SECRET") or os.environ.get("FREESOUND_API_KEY", "")
    if not client_secret:
        raise SystemExit("FREESOUND_CLIENT_SECRET is missing in .env or environment")

    if args.command == "auth-url":
        state = args.state or secrets.token_urlsafe(16)
        print(json.dumps({
            "authorization_url": auth_url(client_id, state),
            "callback_url": os.environ.get("FREESOUND_REDIRECT_URI", DEFAULT_REDIRECT_URI),
            "state": state,
            "next_step": "Open authorization_url, approve access, copy the code shown on the Freesound callback page, then run exchange.",
        }, indent=2))
        return

    if args.command == "exchange":
        data = exchange_code(client_id, client_secret, args.code)
    else:
        data = refresh_access_token(client_id, client_secret, require_env("FREESOUND_REFRESH_TOKEN"))

    values = token_env(data)
    if args.write_env:
        update_env_file(REPO_ROOT / ".env", values)
    print(json.dumps({"env_values": values, "wrote_env": bool(args.write_env)}, indent=2))


if __name__ == "__main__":
    main()
