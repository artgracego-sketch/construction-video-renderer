from __future__ import annotations

import os
from typing import Any

import requests


TOKEN_URL = "https://oauth2.googleapis.com/token"

DRIVE_FILES_URL = (
    "https://www.googleapis.com/drive/v3/files"
)


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


def get_access_token() -> str:
    client_id = require_env(
        "GOOGLE_CLIENT_ID"
    )

    client_secret = require_env(
        "GOOGLE_CLIENT_SECRET"
    )

    refresh_token = require_env(
        "GOOGLE_REFRESH_TOKEN"
    )

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

    if response.status_code != 200:
        try:
            data = response.json()
        except ValueError:
            data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google OAuth token refresh failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": data.get("error"),
                    "error_description": data.get(
                        "error_description"
                    ),
                }
            )
        )

    data = response.json()

    access_token = data.get(
        "access_token"
    )

    if not access_token:
        raise RuntimeError(
            "Google OAuth response did not contain "
            "access_token."
        )

    return access_token


def list_drive_files(
    access_token: str,
) -> list[dict[str, Any]]:
    params = {
        "pageSize": 100,
        "orderBy": "modifiedTime desc",
        "q": "trashed = false",
        "fields": (
            "nextPageToken,"
            "files("
            "id,"
            "name,"
            "mimeType,"
            "size,"
            "modifiedTime,"
            "parents,"
            "trashed,"
            "capabilities/canDownload"
            ")"
        ),
        "spaces": "drive",
        "corpora": "user",
        "includeItemsFromAllDrives": "true",
        "supportsAllDrives": "true",
    }

    response = requests.get(
        DRIVE_FILES_URL,
        params=params,
        headers={
            "Authorization": (
                "Bearer "
                + access_token
            )
        },
        timeout=60,
    )

    if response.status_code != 200:
        try:
            data = response.json()
        except ValueError:
            data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google Drive files.list failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": data.get("error"),
                    "error_description": (
                        data.get("error", {})
                        .get("errors", [{}])[0]
                        .get("message")
                    ),
                }
            )
        )

    data = response.json()

    return data.get(
        "files",
        []
    )


def main() -> None:
    print(
        "Getting Google OAuth access token..."
    )

    access_token = get_access_token()

    print(
        "Google OAuth access token acquired."
    )

    print(
        "Listing Google Drive files..."
    )

    files = list_drive_files(
        access_token
    )

    print(
        f"Visible file count returned: {len(files)}"
    )

    print()
    print(
        "=== Google Drive files ==="
    )

    if not files:
        print(
            "No visible files were returned."
        )
        return

    for index, file in enumerate(
        files,
        start=1
    ):
        print(
            f"[{index}]"
        )

        print(
            f"  name: {file.get('name')}"
        )

        print(
            f"  id: {file.get('id')}"
        )

        print(
            f"  mimeType: {file.get('mimeType')}"
        )

        print(
            f"  size: {file.get('size')}"
        )

        print(
            f"  modifiedTime: "
            f"{file.get('modifiedTime')}"
        )

        print(
            f"  parents: {file.get('parents')}"
        )

        print(
            f"  canDownload: "
            f"{file.get('capabilities', {}).get('canDownload')}"
        )

        print()


if __name__ == "__main__":
    main()
