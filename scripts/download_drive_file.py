from __future__ import annotations

import os
from pathlib import Path

import requests


TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_URL = "https://www.googleapis.com/drive/v3/files"


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


def get_access_token() -> str:
    client_id = require_env("GOOGLE_CLIENT_ID")
    client_secret = require_env("GOOGLE_CLIENT_SECRET")
    refresh_token = require_env("GOOGLE_REFRESH_TOKEN")

    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Google OAuth response did not contain access_token."
        )

    return access_token


def download_file(
    access_token: str,
    file_id: str,
    output_path: Path,
) -> None:

    response = requests.get(
        DRIVE_URL,
        params={
            "alt": "media",
            "fileId": file_id,
        },
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=120,
    )

    response.raise_for_status()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        response.content
    )


def main() -> None:

    file_id = require_env(
        "DRIVE_FILE_ID"
    )

    access_token = get_access_token()

    output = Path(
        "work/drive_input"
    )

    download_file(
        access_token,
        file_id,
        output,
    )

    print(
        f"Downloaded Drive file: {output}"
    )

    print(
        f"Size: {output.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
