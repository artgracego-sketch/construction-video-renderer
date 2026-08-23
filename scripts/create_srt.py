from __future__ import annotations

import json
import os
from pathlib import Path


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


def format_timestamp(seconds: float) -> str:
    """
    秒数をSRT形式へ変換する。

    例:
        3.5
        ↓
        00:00:03,500
    """

    if seconds < 0:
        raise ValueError(
            "Subtitle time cannot be negative."
        )

    milliseconds = int(
        round(seconds * 1000)
    )

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    seconds_value = milliseconds // 1000
    milliseconds %= 1000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds_value:02d},"
        f"{milliseconds:03d}"
    )


def load_subtitle_data() -> list[dict]:
    """
    SUBTITLE_JSONから字幕配列を読み込む。
    """

    raw = require_env(
        "SUBTITLE_JSON"
    )

    try:
        data = json.loads(raw)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "SUBTITLE_JSON is not valid JSON."
        ) from exc

    if not isinstance(data, list):

        raise RuntimeError(
            "SUBTITLE_JSON must be a JSON array."
        )

    return data


def validate_subtitle_item(
    item: object,
    index: int,
) -> tuple[str, float, float]:

    if not isinstance(item, dict):

        raise RuntimeError(
            f"Subtitle item {index} "
            "must be an object."
        )

    text = str(
        item.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        raise RuntimeError(
            f"Subtitle item {index} "
            "has empty text."
        )

    try:

        start_seconds = float(
            item[
                "start_seconds"
            ]
        )

        end_seconds = float(
            item[
                "end_seconds"
            ]
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:

        raise RuntimeError(
            f"Subtitle item {index} "
            "has invalid timing."
        ) from exc

    if start_seconds < 0:

        raise RuntimeError(
            f"Subtitle item {index} "
            "has negative start_seconds."
        )

    if end_seconds <= start_seconds:

        raise RuntimeError(
            f"Subtitle item {index} "
            "must have end_seconds "
            "greater than start_seconds."
        )

    return (
        text,
        start_seconds,
        end_seconds,
    )


def build_srt(
    items: list[dict],
) -> str:

    if not items:

        raise RuntimeError(
            "No subtitle lines were supplied."
        )

    blocks: list[str] = []

    for index, item in enumerate(
        items,
        start=1,
    ):

        text, start_seconds, end_seconds = (
            validate_subtitle_item(
                item,
                index,
            )
        )

        block = (
            f"{index}\n"
            f"{format_timestamp(start_seconds)}"
            f" --> "
            f"{format_timestamp(end_seconds)}\n"
            f"{text}\n"
        )

        blocks.append(
            block
        )

    return "\n".join(
        blocks
    ) + "\n"


def main() -> None:

    output_path = Path(
        os.environ.get(
            "SUBTITLE_OUTPUT_PATH",
            "work/subtitle.srt",
        )
    )

    subtitle_items = (
        load_subtitle_data()
    )

    srt_text = build_srt(
        subtitle_items
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        srt_text,
        encoding="utf-8",
        newline="\n",
    )

    if not output_path.exists():

        raise RuntimeError(
            "SRT file was not created."
        )

    if output_path.stat().st_size <= 0:

        raise RuntimeError(
            "SRT file is empty."
        )

    print(
        "SRT creation succeeded."
    )

    print(
        f"Output: {output_path}"
    )

    print(
        f"Subtitle count: "
        f"{len(subtitle_items)}"
    )

    print()
    print(
        "=== Generated SRT ==="
    )

    print(
        srt_text,
        end=""
    )


if __name__ == "__main__":
    main()
