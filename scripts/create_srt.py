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
    """
    秒数をSRT形式へ変換する。

    例:
        3.5
        -> 00:00:03,500
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


def strip_code_fence(raw: str) -> str:
    """
    ```json
    ...
    ```
    のコードフェンスを除去する。
    """

    text = raw.strip()

    match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return text


def extract_json_value(raw: str) -> Any:
    """
    JSON文字列から実データを抽出する。

    対応:
      1. 配列
      2. JSONオブジェクト
      3. {"subtitle_lines":[...]}
      4. Script全体JSON
      5. コードフェンス付きJSON
      6. JSONの前後に説明文があるケース
    """

    text = strip_code_fence(raw)

    # --------------------------------------------------------
    # 1. まず完全なJSONとして解析
    # --------------------------------------------------------
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # 2. JSONDecoder.raw_decodeで先頭JSONだけ読む
    #
    # 例:
    #   [{"text":"..."}] 余分な文字
    # --------------------------------------------------------
    decoder = json.JSONDecoder()

    try:
        value, end_index = decoder.raw_decode(text)

        trailing = text[end_index:].strip()

        if not trailing:
            return value

        # 後ろに余計な文字がある場合でも、
        # 読み取れたJSONが有効なら採用する。
        if isinstance(value, (list, dict)):
            return value

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # 3. 文字列中からJSON配列を探す
    # --------------------------------------------------------
    array_start = text.find("[")

    if array_start >= 0:

        try:
            value, end_index = decoder.raw_decode(
                text[array_start:]
            )

            if isinstance(value, list):
                return value

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # 4. 文字列中からJSONオブジェクトを探す
    # --------------------------------------------------------
    object_start = text.find("{")

    if object_start >= 0:

        try:
            value, end_index = decoder.raw_decode(
                text[object_start:]
            )

            if isinstance(value, dict):
                return value

        except json.JSONDecodeError:
            pass

    raise RuntimeError(
        "SUBTITLE_JSONから有効なJSONを抽出できませんでした。"
    )


def extract_subtitle_items(raw: str) -> list[dict]:
    """
    以下のどれでもsubtitle_linesを抽出する。

    配列:
      [...]

    オブジェクト:
      {"subtitle_lines":[...]}

    Script全体:
      {
        "success": true,
        "script": {
          "subtitle_lines": [...]
        }
      }
    """

    data = extract_json_value(raw)

    # --------------------------------------------------------
    # 1. 直接配列
    # --------------------------------------------------------
    if isinstance(data, list):

        return data

    # --------------------------------------------------------
    # 2. オブジェクト
    # --------------------------------------------------------
    if isinstance(data, dict):

        subtitle_lines = data.get(
            "subtitle_lines"
        )

        if isinstance(
            subtitle_lines,
            list,
        ):
            return subtitle_lines

        # success + script の形式
        script = data.get(
            "script"
        )

        if isinstance(
            script,
            dict,
        ):

            subtitle_lines = script.get(
                "subtitle_lines"
            )

            if isinstance(
                subtitle_lines,
                list,
            ):
                return subtitle_lines

        # script自体が直接入っているケース
        nested_script = data.get(
            "data"
        )

        if isinstance(
            nested_script,
            dict,
        ):

            subtitle_lines = nested_script.get(
                "subtitle_lines"
            )

            if isinstance(
                subtitle_lines,
                list,
            ):
                return subtitle_lines

    raise RuntimeError(
        "SUBTITLE_JSON内にsubtitle_lines配列が見つかりません。"
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

    raw = require_env(
        "SUBTITLE_JSON"
    )

    output_path = Path(
        os.environ.get(
            "SUBTITLE_OUTPUT_PATH",
            "work/subtitle.srt",
        )
    )

    subtitle_items = extract_subtitle_items(
        raw
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
        end="",
    )


if __name__ == "__main__":
    main()
