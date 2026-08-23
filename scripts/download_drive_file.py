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
            error_data = response.json()

        except ValueError:

            error_data = {
                "raw":
                    response.text[:500]
            }


        safe_error = {

            "http_status":
                response.status_code,

            "error":
                error_data.get(
                    "error"
                ),

            "error_description":
                error_data.get(
                    "error_description"
                ),
        }


        raise RuntimeError(

            "Google OAuth token refresh failed: "
            +
            str(safe_error)

        )


    data = response.json()


    access_token =
        data.get(
            "access_token"
        )


    if not access_token:

        raise RuntimeError(
            "Google OAuth response did not "
            "contain access_token."
        )


    return access_token


def download_file(
    access_token: str,
    file_id: str,
    output_path: Path,
) -> None:

    if not file_id:

        raise ValueError(
            "Google Drive file ID is empty."
        )


    response = requests.get(

        DRIVE_FILES_URL +

        "/" +

        file_id,

        params={
            "alt": "media"
        },

        headers={
            "Authorization":
                f"Bearer {access_token}"
        },

        timeout=120,
    )


    if response.status_code != 200:

        try:
            error_data =
                response.json()

        except ValueError:

            error_data = {
                "raw":
                    response.text[:500]
            }


        safe_error = {

            "http_status":
                response.status_code,

            "error":
                error_data.get(
                    "error"
                ),

        }


        raise RuntimeError(

            "Google Drive download failed: "
            +
            str(safe_error)

        )


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_path.write_bytes(
        response.content
    )


    if not output_path.exists():

        raise RuntimeError(
            "Download completed but "
            "output file was not created."
        )


    size =
        output_path.stat().st_size


    if size <= 0:

        raise RuntimeError(
            "Downloaded file is empty."
        )


def main() -> None:

    file_id = require_env(
        "DRIVE_FILE_ID"
    )


    access_token =
        get_access_token()


    output_path =
        Path(
            "work/drive_input"
        )


    print(
        "Google OAuth access token acquired."
    )


    print(
        "Downloading Google Drive file..."
    )


    download_file(

        access_token,

        file_id,

        output_path

    )


    print(
        "Download successful."
    )


    print(
        f"Output: {output_path}"
    )


    print(
        f"Size: {output_path.stat().st_size} bytes"
    )


if __name__ == "__main__":

    main()
