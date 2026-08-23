from __future__ import annotations

import os
from pathlib import Path

import requests


TOKEN_URL = "https://oauth2.googleapis.com/token"

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


def get_access_token() -> str:
    """Refresh TokenからGoogle Access Tokenを取得する。"""

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

    if response.status_code != 200:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google OAuth token refresh failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": error_data.get("error"),
                    "error_description": error_data.get(
                        "error_description"
                    ),
                }
            )
        )

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Google OAuth response did not contain "
            "access_token."
        )

    return access_token


def get_file_metadata(
    access_token: str,
    file_id: str,
) -> dict:
    """Google Driveファイルのメタデータを取得する。"""

    url = f"{DRIVE_FILES_URL}/{file_id}"

    response = requests.get(
        url,
        params={
            "fields": (
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "trashed,"
                "parents,"
                "capabilities/canDownload,"
                "driveId"
            ),
            "supportsAllDrives": "true",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )

    if response.status_code != 200:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google Drive metadata lookup failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": error_data.get("error"),
                    "error_description": (
                        error_data.get("error", {})
                        .get("errors", [{}])[0]
                        .get("message")
                    ),
                }
            )
        )

    return response.json()


def download_file(
    access_token: str,
    file_id: str,
    output_path: Path,
) -> None:
    """Google Driveからファイル本体をダウンロードする。"""

    if not file_id:
        raise ValueError(
            "Google Drive file ID is empty."
        )

    metadata = get_file_metadata(
        access_token,
        file_id,
    )

    print("Drive file metadata:")
    print(
        {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "mimeType": metadata.get("mimeType"),
            "size": metadata.get("size"),
            "trashed": metadata.get("trashed"),
            "driveId": metadata.get("driveId"),
            "canDownload": (
                metadata.get("capabilities", {})
                .get("canDownload")
            ),
        }
    )

    if metadata.get("trashed"):
        raise RuntimeError(
            "指定ファイルはゴミ箱にあります。"
        )

    can_download = (
        metadata.get("capabilities", {})
        .get("canDownload")
    )

    if can_download is False:
        raise RuntimeError(
            "指定ファイルはダウンロードできません。"
        )

    url = f"{DRIVE_FILES_URL}/{file_id}"

    response = requests.get(
        url,
        params={
            "alt": "media",
            "supportsAllDrives": "true",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=120,
    )

    if response.status_code != 200:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google Drive download failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": error_data.get("error"),
                }
            )
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        response.content
    )

    size = output_path.stat().st_size

    if size <= 0:
        raise RuntimeError(
            "Downloaded file is empty."
        )

    print(
        f"Downloaded file: {output_path}"
    )

    print(
        f"Downloaded size: {size} bytes"
    )


def main() -> None:
    """メイン処理。"""

    file_id = require_env(
        "DRIVE_FILE_ID"
    )

    print(
        "Getting Google OAuth access token..."
    )

    access_token = get_access_token()

    print(
        "Google OAuth access token acquired."
    )

    output_path = Path(
        "work/drive_input"
    )

    print(
        "Downloading Google Drive file..."
    )

    download_file(
        access_token,
        file_id,
        output_path,
    )

    print(
        "Drive download test succeeded."
    )


if __name__ == "__main__":
    main()
