from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests


TOKEN_URL = "https://oauth2.googleapis.com/token"

DRIVE_FILES_URL = (
    "https://www.googleapis.com/drive/v3/files"
)

DRIVE_UPLOAD_URL = (
    "https://www.googleapis.com/upload/drive/v3/files"
)

CHUNK_SIZE = 5 * 1024 * 1024


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
                "raw": response.text[:1000]
            }

        raise RuntimeError(
            "Google OAuth token refresh failed: "
            + str(
                {
                    "http_status": response.status_code,
                    "error": data.get("error"),
                    "error_description": (
                        data.get(
                            "error_description"
                        )
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
    return (
        value
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )


def find_output_folder(
    access_token: str,
    folder_id: str,
) -> dict[str, Any]:

    params = {
        "fields": (
            "id,name,mimeType,trashed,"
            "capabilities/canAddChildren"
        ),
        "supportsAllDrives": "true",
    }

    response = requests.get(
        f"{DRIVE_FILES_URL}/{folder_id}",
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
                "raw": response.text[:1000]
            }

        raise RuntimeError(
            "Google Drive output folder lookup failed: "
            + str(
                {
                    "http_status": (
                        response.status_code
                    ),
                    "error": data.get("error"),
                    "error_description": (
                        data.get("error", {})
                        .get("errors", [{}])[0]
                        .get("message")
                    ),
                }
            )
        )

    folder = response.json()

    if folder.get("trashed"):
        raise RuntimeError(
            "Google Drive output folder is trashed."
        )

    if (
        folder.get("mimeType")
        != "application/vnd.google-apps.folder"
    ):
        raise RuntimeError(
            "GOOGLE_DRIVE_OUTPUT_FOLDER_ID does not "
            "refer to a folder."
        )

    can_add_children = (
        folder.get("capabilities", {})
        .get("canAddChildren")
    )

    if can_add_children is False:
        raise RuntimeError(
            "The OAuth user cannot add files to "
            "the Google Drive output folder."
        )

    return folder


def upload_resumable(
    access_token: str,
    input_path: Path,
    file_name: str,
    folder_id: str,
) -> dict[str, Any]:

    mime_type = (
        mimetypes.guess_type(
            file_name
        )[0]
        or "application/octet-stream"
    )

    metadata = {
        "name": file_name,
        "parents": [folder_id],
        "mimeType": mime_type,
    }

    print()
    print("=== Starting Google Drive resumable upload ===")
    print(f"File: {input_path}")
    print(f"Name: {file_name}")
    print(f"MIME type: {mime_type}")
    print(f"Folder ID: {folder_id}")
    print(
        f"Size: {input_path.stat().st_size} bytes"
    )

    response = requests.post(
        DRIVE_UPLOAD_URL,
        params={
            "uploadType": "resumable",
            "supportsAllDrives": "true",
            "fields": (
                "id,name,mimeType,size,"
                "webViewLink,parents"
            ),
        },
        headers={
            "Authorization": (
                "Bearer "
                + access_token
            ),
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(
                input_path.stat().st_size
            ),
        },
        data=json.dumps(metadata),
        timeout=60,
    )

    if response.status_code not in (200, 201):
        try:
            data = response.json()
        except ValueError:
            data = {
                "raw": response.text[:1000]
            }

        raise RuntimeError(
            "Failed to start Google Drive resumable "
            "upload: "
            + str(
                {
                    "http_status": (
                        response.status_code
                    ),
                    "error": data.get("error"),
                    "error_description": (
                        data.get("error", {})
                        .get("errors", [{}])[0]
                        .get("message")
                    ),
                }
            )
        )

    upload_url = response.headers.get(
        "Location"
    )

    if not upload_url:
        raise RuntimeError(
            "Google Drive resumable upload did not "
            "return a Location header."
        )

    total_size = input_path.stat().st_size
    uploaded = 0

    with input_path.open("rb") as file_handle:

        while uploaded < total_size:

            chunk = file_handle.read(
                CHUNK_SIZE
            )

            if not chunk:
                raise RuntimeError(
                    "Unexpected end of file during "
                    "Google Drive upload."
                )

            start = uploaded
            end = uploaded + len(chunk) - 1

            chunk_response = requests.put(
                upload_url,
                headers={
                    "Content-Length": str(
                        len(chunk)
                    ),
                    "Content-Range": (
                        f"bytes {start}-{end}/"
                        f"{total_size}"
                    ),
                    "Content-Type": mime_type,
                },
                data=chunk,
                timeout=300,
            )

            if chunk_response.status_code in (
                200,
                201,
            ):
                uploaded = end + 1

                try:
                    result = (
                        chunk_response.json()
                    )
                except ValueError:
                    result = {}

                print(
                    "Google Drive upload completed."
                )

                return result

            if chunk_response.status_code == 308:
                range_header = (
                    chunk_response.headers.get(
                        "Range"
                    )
                )

                if range_header:
                    try:
                        uploaded = (
                            int(
                                range_header
                                .split("-")[-1]
                            )
                            + 1
                        )
                    except (
                        ValueError,
                        IndexError,
                    ):
                        uploaded = end + 1
                else:
                    uploaded = end + 1

                percentage = (
                    uploaded
                    / total_size
                    * 100
                )

                print(
                    "Upload progress: "
                    f"{uploaded}/"
                    f"{total_size} bytes "
                    f"({percentage:.1f}%)"
                )

                continue

            try:
                data = chunk_response.json()
            except ValueError:
                data = {
                    "raw": (
                        chunk_response.text[:1000]
                    )
                }

            raise RuntimeError(
                "Google Drive upload failed: "
                + str(
                    {
                        "http_status": (
                            chunk_response.status_code
                        ),
                        "error": data.get("error"),
                        "error_description": (
                            data.get(
                                "error_description"
                            )
                            or data.get("error", {})
                            .get("errors", [{}])[0]
                            .get("message")
                        ),
                    }
                )
            )

    raise RuntimeError(
        "Google Drive upload ended without "
        "returning a completed file."
    )


def main() -> None:

    input_path_text = require_env(
        "DRIVE_UPLOAD_INPUT_PATH"
    ).strip()

    output_name = require_env(
        "DRIVE_UPLOAD_FILE_NAME"
    ).strip()

    folder_id = require_env(
        "GOOGLE_DRIVE_OUTPUT_FOLDER_ID"
    ).strip()

    if not input_path_text:
        raise RuntimeError(
            "DRIVE_UPLOAD_INPUT_PATH is empty."
        )

    if not output_name:
        raise RuntimeError(
            "DRIVE_UPLOAD_FILE_NAME is empty."
        )

    if not folder_id:
        raise RuntimeError(
            "GOOGLE_DRIVE_OUTPUT_FOLDER_ID is empty."
        )

    input_path = Path(
        input_path_text
    )

    if not input_path.is_file():
        raise RuntimeError(
            "Upload input file does not exist: "
            + str(input_path)
        )

    file_size = input_path.stat().st_size

    if file_size <= 0:
        raise RuntimeError(
            "Upload input file is empty."
        )

    print(
        "Getting Google OAuth access token..."
    )

    access_token = get_access_token()

    print(
        "Google OAuth access token acquired."
    )

    print()
    print(
        "Checking Google Drive output folder..."
    )

    folder = find_output_folder(
        access_token,
        folder_id,
    )

    print(
        f"Output folder: "
        f"{folder.get('name')}"
    )

    print(
        f"Output folder ID: "
        f"{folder.get('id')}"
    )

    result = upload_resumable(
        access_token=access_token,
        input_path=input_path,
        file_name=output_name,
        folder_id=folder_id,
    )

    uploaded_id = result.get("id")

    if not uploaded_id:
        raise RuntimeError(
            "Google Drive upload response did not "
            "contain a file ID."
        )

    print()
    print(
        "=== Google Drive upload succeeded ==="
    )

    print(
        f"name: {result.get('name')}"
    )

    print(
        f"id: {uploaded_id}"
    )

    print(
        f"mimeType: {result.get('mimeType')}"
    )

    print(
        f"size: {result.get('size')}"
    )

    print(
        f"parents: {result.get('parents')}"
    )

    print(
        f"webViewLink: "
        f"{result.get('webViewLink')}"
    )


if __name__ == "__main__":
    main()
