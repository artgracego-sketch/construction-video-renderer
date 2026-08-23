from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"

# ------------------------------------------------------------
# Google Driveから取得した実画像を優先
#
# DRIVE_INPUT_PATH が指定されていれば、それを使用する。
# 指定されていない場合だけ、旧テスト用 input/photo.png
# を使用する。
# ------------------------------------------------------------
DEFAULT_PHOTO = INPUT_DIR / "photo.png"

AUDIO = INPUT_DIR / "narration.wav"
SUBTITLE = INPUT_DIR / "subtitle.srt"

OUTPUT = OUTPUT_DIR / "output.mp4"


def get_photo_path() -> Path:
    """
    動画生成に使用する画像ファイルを決定する。

    優先順位:
      1. DRIVE_INPUT_PATH
      2. input/photo.png
    """

    drive_input = os.environ.get(
        "DRIVE_INPUT_PATH"
    )

    if drive_input:
        path = Path(
            drive_input
        ).resolve()

        if not path.exists():
            raise FileNotFoundError(
                "DRIVE_INPUT_PATH does not exist: "
                + str(path)
            )

        if not path.is_file():
            raise RuntimeError(
                "DRIVE_INPUT_PATH is not a file: "
                + str(path)
            )

        return path

    if DEFAULT_PHOTO.exists():
        return DEFAULT_PHOTO

    raise FileNotFoundError(
        "No input photo was found.\n"
        "Expected either:\n"
        "- DRIVE_INPUT_PATH\n"
        "- input/photo.png"
    )


def get_ffmpeg_path() -> str:
    """
    imageio-ffmpegが提供するFFmpegを優先する。
    見つからない場合のみPATHを確認する。
    """

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
) -> None:

    required = [
        photo,
        AUDIO,
        SUBTITLE,
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


def render(
    photo: Path,
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

    command = [

        ffmpeg,

        "-y",

        # ----------------------------------------------------
        # Input image
        # ----------------------------------------------------
        "-loop",
        "1",

        "-i",
        str(photo),

        # ----------------------------------------------------
        # Narration
        # ----------------------------------------------------
        "-i",
        str(AUDIO),

        # ----------------------------------------------------
        # Video processing
        # ----------------------------------------------------
        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:(oh-ih)/2,"
            "subtitles="
            + str(SUBTITLE)
        ),

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------
        "-t",
        "15",

        # ----------------------------------------------------
        # Frame rate
        # ----------------------------------------------------
        "-r",
        "30",

        # ----------------------------------------------------
        # Mapping
        # ----------------------------------------------------
        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        # ----------------------------------------------------
        # Video codec
        # ----------------------------------------------------
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        # ----------------------------------------------------
        # Audio codec
        # ----------------------------------------------------
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # ----------------------------------------------------
        # Compatibility
        # ----------------------------------------------------
        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        # ----------------------------------------------------
        # Never exceed shortest input
        # ----------------------------------------------------
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
        "=== Select photo ==="
    )

    photo = get_photo_path()

    print(
        "Photo selected:"
    )

    print(
        photo
    )

    print(
        "=== Validate input ==="
    )

    validate_inputs(
        photo
    )

    print(
        "=== Render ==="
    )

    render(
        photo
    )

    print(
        "=== Inspect output ==="
    )

    inspect_output()


if __name__ == "__main__":

    main()
