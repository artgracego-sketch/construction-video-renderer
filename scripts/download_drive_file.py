from __future__ import annotations

import os
from pathlib import Path

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


def escape_drive_query_value(
    value: str,
) -> str:
    """
    Google Drive APIのq文字列用に
    バックスラッシュとシングルクォートを
    エスケープする。
    """

    return (
        value
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )


def find_files_by_name(
    access_token: str,
    file_name: str,
) -> list[dict]:
    """
    Google Driveから完全一致のファイル名を検索する。
    """

    escaped_name = (
        escape_drive_query_value(
            file_name
        )
    )

    query = (
        f"name = '{escaped_name}' "
        "and trashed = false"
    )

    params = {
        "pageSize": 100,
        "orderBy": "modifiedTime desc",
        "q": query,
        "fields": (
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
            "Google Drive file search failed: "
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


def download_file(
    access_token: str,
    file_id: str,
    output_path: Path,
) -> None:
    """
    Google Driveから実ファイルを取得する。
    """

    url = (
        f"{DRIVE_FILES_URL}/{file_id}"
    )

    response = requests.get(
        url,
        params={
            "alt": "media",
            "supportsAllDrives": "true",
        },
        headers={
            "Authorization": (
                f"Bearer {access_token}"
            )
        },
        timeout=120,
    )

    if response.status_code != 200:
        try:
            data = response.json()
        except ValueError:
            data = {
                "raw": response.text[:500]
            }

        raise RuntimeError(
            "Google Drive download failed: "
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


def main() -> None:
    file_name = require_env(
        "DRIVE_FILE_NAME"
    ).strip()

    if not file_name:
        raise RuntimeError(
            "DRIVE_FILE_NAME is empty."
        )

    print(
        "Getting Google OAuth access token..."
    )

    access_token = get_access_token()

    print(
        "Google OAuth access token acquired."
    )

    print(
        "Searching Google Drive:"
    )

    print(
        file_name
    )

    files = find_files_by_name(
        access_token,
        file_name,
    )

    if not files:
        raise RuntimeError(
            "Google Drive file not found by name: "
            + file_name
        )

    print(
        f"Matching files: {len(files)}"
    )

    for index, file in enumerate(
        files,
        start=1
    ):
        print(
            f"[{index}] "
            f"name={file.get('name')!r} "
            f"id={file.get('id')} "
            f"mimeType={file.get('mimeType')} "
            f"modifiedTime={file.get('modifiedTime')}"
        )

    selected = files[0]

    selected_id = selected.get(
        "id"
    )

    selected_name = selected.get(
        "name"
    )

    selected_mime = selected.get(
        "mimeType"
    )

    if not selected_id:
        raise RuntimeError(
            "Matched Google Drive file has no file ID."
        )

    if selected_mime == "application/vnd.google-apps.folder":
        raise RuntimeError(
            "The matched item is a folder, not a file."
        )

    can_download = (
        selected
        .get("capabilities", {})
        .get("canDownload")
    )

    if can_download is False:
        raise RuntimeError(
            "The matched file cannot be downloaded "
            "by this OAuth user."
        )

    print()
    print(
        "Selected file:"
    )

    print(
        f"name: {selected_name}"
    )

    print(
        f"id: {selected_id}"
    )

    print(
        f"mimeType: {selected_mime}"
    )

    output_path = Path(
        "work/drive_input"
    )

    print()
    print(
        "Downloading Google Drive file..."
    )

    download_file(
        access_token,
        selected_id,
        output_path,
    )

    print(
        "Drive download test succeeded."
    )

    print(
        f"Output: {output_path}"
    )

    print(
        f"Size: "
        f"{output_path.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
