def get_file_metadata(
    access_token: str,
    file_id: str,
) -> dict:
    """Driveファイルのメタデータを取得する。"""

    url = (
        DRIVE_FILE_URL
        + "/"
        + file_id
    )

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
                "capabilities(canDownload),"
                "driveId"
            ),
            "supportsAllDrives": "true",
        },
        headers={
            "Authorization": (
                "Bearer "
                + access_token
            )
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
            + str({
                "http_status": response.status_code,
                "error": error_data.get("error"),
            })
        )

    return response.json()


def download_file(
    access_token: str,
    file_id: str,
    output_path: Path,
) -> None:
    """DriveのBlobファイルをダウンロードする。"""

    metadata = get_file_metadata(
        access_token,
        file_id,
    )

    print(
        "Drive file metadata:"
    )

    print(
        {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "mimeType": metadata.get("mimeType"),
            "size": metadata.get("size"),
            "trashed": metadata.get("trashed"),
            "driveId": metadata.get("driveId"),
            "canDownload": (
                metadata
                .get("capabilities", {})
                .get("canDownload")
            ),
        }
    )

    if metadata.get("trashed"):
        raise RuntimeError(
            "指定ファイルはゴミ箱にあります。"
        )

    capabilities = metadata.get(
        "capabilities",
        {}
    )

    if (
        capabilities.get("canDownload")
        is False
    ):
        raise RuntimeError(
            "指定ファイルはダウンロードできません。"
        )

    url = (
        DRIVE_FILE_URL
        + "/"
        + file_id
    )

    response = requests.get(
        url,
        params={
            "alt": "media",
            "supportsAllDrives": "true",
        },
        headers={
            "Authorization": (
                "Bearer "
                + access_token
            )
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
            + str({
                "http_status": response.status_code,
                "error": error_data.get("error"),
            })
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
        f"Downloaded {metadata.get('name')} "
        f"({size} bytes)"
    )
