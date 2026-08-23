from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def require_env(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


def format_timestamp(seconds: float) -> str:
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


def strip_code_fence(text: str) -> str:
    text = text.strip()

    match = re.fullmatch(
        r"```(?:json|javascript|js)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return text


def try_parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_json_candidates(
    raw: str,
) -> list[Any]:
    """
    入力文字列からJSON候補を複数抽出する。

    対応:
    - JSONそのもの
    - ```json ... ```
    - JSONの前後にログや説明文がある
    - JSON配列だけ
    - JSONオブジェクトだけ
    """

    candidates: list[Any] = []

    cleaned = strip_code_fence(
        raw
    )

    direct = try_parse_json(
        cleaned
    )

    if direct is not None:
        candidates.append(
            direct
        )

    decoder = json.JSONDecoder()

    # --------------------------------------------------------
    # 文字列の中にあるJSONオブジェクト/配列を順番に探す
    # --------------------------------------------------------
    positions = []

    for char in ("{", "["):
        start = 0

        while True:
            index = cleaned.find(
                char,
                start
            )

            if index < 0:
                break

            positions.append(
                index
            )

            start = index + 1

    for position in sorted(
        set(positions)
    ):
        fragment = cleaned[position:]

        try:
            value, _ = decoder.raw_decode(
                fragment
            )

        except json.JSONDecodeError:
            continue

        if value is not None:
            candidates.append(
                value
            )

    return candidates


def find_subtitle_lines_recursive(
    value: Any,
) -> list[dict] | None:
    """
    JSON構造を再帰的に探索し、
    subtitle_lines を発見する。

    例:
      {
        "script": {
          "subtitle_lines": [...]
        }
      }

    だけでなく、さらに深い階層にも対応する。
    """

    if isinstance(
        value,
        dict,
    ):

        if "subtitle_lines" in value:

            subtitle_lines = (
                value["subtitle_lines"]
            )

            if isinstance(
                subtitle_lines,
                list,
            ):

                return subtitle_lines

        for child in value.values():

            result = (
                find_subtitle_lines_recursive(
                    child
                )
            )

            if result is not None:
                return result

        return None

    if isinstance(
        value,
        list,
    ):

        # 配列そのものが字幕項目の場合
        if (
            value
            and all(
                isinstance(
                    item,
                    dict,
                )
                for item in value
            )
        ):

            if all(
                (
                    "text" in item
                    and
                    (
                        "start_seconds"
                        in item
                    )
                    and
                    (
                        "end_seconds"
                        in item
                    )
                )
                for item in value
            ):

                return value

        for child in value:

            result = (
                find_subtitle_lines_recursive(
                    child
                )
            )

            if result is not None:
                return result

    return None


def extract_subtitle_items(
    raw: str,
) -> list[dict]:
    candidates = extract_json_candidates(
        raw
    )

    for candidate in candidates:

        result = (
            find_subtitle_lines_recursive(
                candidate
            )
        )

        if result is not None:
            return result

    raise RuntimeError(
        "SUBTITLE_JSONからsubtitle_lines配列を取得できませんでした。"
        "\n"
        "今回受け取った入力長: "
        + str(len(raw))
        + " 文字"
        + "\n"
        "入力にsubtitle_linesが含まれているか確認してください。"
    )


def validate_subtitle_item(
    item: object,
    index: int,
) -> tuple[str, float, float]:

    if not isinstance(
        item,
        dict,
    ):

        raise RuntimeError(
            f"Subtitle item {index} "
            "must be an object."
        )

    text = str(
        item.get(
            "text",
            "",
        )
    ).strip()

    if not text:

        raise RuntimeError(
            f"Subtitle item {index} "
            "has empty text."
        )

    try:

        start_seconds = float(
            item["start_seconds"]
        )

        end_seconds = float(
            item["end_seconds"]
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

        (
            text,
            start_seconds,
            end_seconds,
        ) = validate_subtitle_item(
            item,
            index,
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

    return (
        "\n".join(
            blocks
        )
        + "\n"
    )


def main() -> None:

    raw = require_env(
        "SUBTITLE_JSON"
    )

    output_path = Path(
        os.environ.get(
            "SUBTITLE_OUTPUT_PATH",
            "work/subtitle.srt",
        )
    )

    print(
        "Reading subtitle input..."
    )

    print(
        f"Input length: {len(raw)} characters"
    )

    subtitle_items = (
        extract_subtitle_items(
            raw
        )
    )

    print(
        f"Subtitle lines found: "
        f"{len(subtitle_items)}"
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

    print()
    print(
        "=== Generated SRT ==="
    )

    print(
        srt_text,
        end="",
    )


if __name__ == "__main__":
    main()
