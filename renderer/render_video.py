from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"

DEFAULT_PHOTO = INPUT_DIR / "photo.png"
DEFAULT_AUDIO = INPUT_DIR / "narration.wav"
DEFAULT_SUBTITLE = INPUT_DIR / "subtitle.srt"

OUTPUT = OUTPUT_DIR / "output.mp4"


def get_input_path(
    environment_name: str,
    fallback_path: Path,
    label: str,
) -> Path:

    external_path = os.environ.get(
        environment_name
    )

    if external_path:

        path = Path(
            external_path
        ).resolve()

        if not path.exists():

            raise FileNotFoundError(
                f"{label} does not exist: "
                + str(path)
            )

        if not path.is_file():

            raise RuntimeError(
                f"{label} is not a file: "
                + str(path)
            )

        return path

    if fallback_path.exists():

        return fallback_path

    raise FileNotFoundError(
        f"No {label} was found.\n"
        f"Expected either:\n"
        f"- {environment_name}\n"
        f"- {fallback_path}"
    )


def get_ffmpeg_path() -> str:

    try:

        ffmpeg_path = (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

        if ffmpeg_path:

            path = Path(
                ffmpeg_path
            )

            if path.exists():

                return str(path)

    except Exception as exc:

        print(
            "imageio-ffmpeg lookup failed:",
            exc,
        )

    system_ffmpeg = shutil.which(
        "ffmpeg"
    )

    if system_ffmpeg:

        return system_ffmpeg

    raise FileNotFoundError(
        "FFmpeg executable was not found."
    )


def escape_filter_path(
    path: Path,
) -> str:
    """
    FFmpeg subtitles filter用のパスを
    安全な文字列へ変換する。

    Linux runnerでは通常 ':' は存在しないが、
    バックスラッシュ等も考慮する。
    """

    value = str(
        path.resolve()
    )

    value = value.replace(
        "\\",
        "\\\\"
    )

    value = value.replace(
        ":",
        "\\:"
    )

    value = value.replace(
        "'",
        "\\'"
    )

    return value


def build_subtitle_filter(
    subtitle: Path,
) -> str:
    """
    libassを使用した日本語字幕フィルタ。

    日本語フォント:
      Noto Sans CJK JP
    """

    subtitle_path = (
        escape_filter_path(
            subtitle
        )
    )

    force_style = (
        "FontName=Noto Sans CJK JP,"
        "FontSize=26,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginV=90"
    )

    return (
        "subtitles="
        + subtitle_path
        + ":charenc=UTF-8"
        + ":force_style='"
        + force_style
        + "'"
    )


def run_ffmpeg(
    command: list[str],
) -> None:

    print(
        "Running:"
    )

    print(
        " ".join(
            command
        )
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    print(
        result.stdout
    )

    if result.returncode != 0:

        raise RuntimeError(
            "FFmpeg failed with exit code "
            + str(
                result.returncode
            )
        )


def validate_inputs(
    photo: Path,
    audio: Path,
    subtitle: Path,
) -> None:

    required = [
        photo,
        audio,
        subtitle,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:

        raise FileNotFoundError(
            "Missing input files:\n"
            + "\n".join(
                missing
            )
        )

    if subtitle.stat().st_size <= 0:

        raise RuntimeError(
            "Subtitle file is empty: "
            + str(subtitle)
        )


def print_subtitle_content(
    subtitle: Path,
) -> None:

    print(
        "=== Subtitle file content ==="
    )

    try:

        content = (
            subtitle
            .read_text(
                encoding="utf-8"
            )
        )

        print(
            content
        )

    except UnicodeDecodeError as exc:

        raise RuntimeError(
            "Subtitle file is not valid UTF-8."
        ) from exc


def render(
    photo: Path,
    audio: Path,
    subtitle: Path,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ffmpeg = get_ffmpeg_path()

    print(
        "FFmpeg executable:"
    )

    print(
        ffmpeg
    )

    print(
        "Selected photo:"
    )

    print(
        photo
    )

    print(
        "Selected audio:"
    )

    print(
        audio
    )

    print(
        "Selected subtitle:"
    )

    print(
        subtitle
    )

    subtitle_filter = (
        build_subtitle_filter(
            subtitle
        )
    )

    print(
        "Subtitle filter:"
    )

    print(
        subtitle_filter
    )

    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease,"
        "pad=1080:1920:"
        "(ow-iw)/2:(oh-ih)/2,"
        + subtitle_filter
    )

    command = [

        ffmpeg,

        "-y",

        "-hide_banner",

        "-loglevel",
        "info",

        "-loop",
        "1",

        "-i",
        str(photo),

        "-i",
        str(audio),

        "-vf",
        video_filter,

        "-t",
        "15",

        "-r",
        "30",

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        "-shortest",

        str(OUTPUT),
    ]

    run_ffmpeg(
        command
    )


def inspect_output() -> None:

    if not OUTPUT.exists():

        raise RuntimeError(
            "FFmpeg finished but output.mp4 "
            "was not created."
        )

    size = OUTPUT.stat().st_size

    if size <= 0:

        raise RuntimeError(
            "output.mp4 was created but is empty."
        )

    print(
        "SUCCESS: "
        + str(OUTPUT)
    )

    print(
        "SIZE: "
        + str(size)
        + " bytes"
    )


def main() -> None:

    print(
        "=== Select inputs ==="
    )

    photo = get_input_path(
        "DRIVE_INPUT_PATH",
        DEFAULT_PHOTO,
        "photo input",
    )

    audio = get_input_path(
        "DRIVE_AUDIO_PATH",
        DEFAULT_AUDIO,
        "audio input",
    )

    subtitle = get_input_path(
        "DRIVE_SUBTITLE_PATH",
        DEFAULT_SUBTITLE,
        "subtitle input",
    )

    print(
        "=== Selected inputs ==="
    )

    print(
        f"Photo: {photo}"
    )

    print(
        f"Audio: {audio}"
    )

    print(
        f"Subtitle: {subtitle}"
    )

    print(
        "=== Validate input ==="
    )

    validate_inputs(
        photo,
        audio,
        subtitle,
    )

    print_subtitle_content(
        subtitle
    )

    print(
        "=== Render ==="
    )

    render(
        photo,
        audio,
        subtitle,
    )

    print(
        "=== Inspect output ==="
    )

    inspect_output()


if __name__ == "__main__":
    main()
