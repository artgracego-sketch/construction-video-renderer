from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"

PHOTO = INPUT_DIR / "photo.png"
AUDIO = INPUT_DIR / "narration.wav"
SUBTITLE = INPUT_DIR / "subtitle.srt"

OUTPUT = OUTPUT_DIR / "output.mp4"


def get_ffmpeg_path() -> str:
    """
    Pythonから確実にFFmpeg実行ファイルを取得する。

    優先順位:
      1. imageio-ffmpegが管理するFFmpeg
      2. OSのPATHにあるffmpeg
    """

    try:
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        if ffmpeg_path:
            path = Path(ffmpeg_path)

            if path.exists():
                return str(path)

    except Exception as exc:
        print(
            "imageio-ffmpeg lookup failed:",
            exc,
        )


    system_ffmpeg = shutil.which("ffmpeg")

    if system_ffmpeg:
        return system_ffmpeg


    raise FileNotFoundError(
        "FFmpeg executable was not found.\n"
        "imageio-ffmpeg path lookup failed "
        "and system PATH does not contain ffmpeg."
    )


def run_ffmpeg(command: list[str]) -> None:

    print(
        "Running:"
    )

    print(
        " ".join(command)
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
            f"{result.returncode}"
        )


def validate_inputs() -> None:

    required = [
        PHOTO,
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
            +
            "\n".join(
                missing
            )
        )


def render() -> None:

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


    command = [

        ffmpeg,

        "-y",

        # -----------------------------------------------------
        # Still image
        # -----------------------------------------------------
        "-loop",
        "1",

        "-i",
        str(PHOTO),

        # -----------------------------------------------------
        # Narration
        # -----------------------------------------------------
        "-i",
        str(AUDIO),

        # -----------------------------------------------------
        # Video
        # -----------------------------------------------------
        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:(oh-ih)/2,"
            "subtitles="
            + str(SUBTITLE)
        ),

        # -----------------------------------------------------
        # Fixed maximum duration
        # -----------------------------------------------------
        "-t",
        "15",

        # -----------------------------------------------------
        # FPS
        # -----------------------------------------------------
        "-r",
        "30",

        # -----------------------------------------------------
        # Mapping
        # -----------------------------------------------------
        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        # -----------------------------------------------------
        # Video encoding
        # -----------------------------------------------------
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        # -----------------------------------------------------
        # Audio encoding
        # -----------------------------------------------------
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # -----------------------------------------------------
        # Compatibility
        # -----------------------------------------------------
        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        # -----------------------------------------------------
        # Do not exceed shortest input
        # -----------------------------------------------------
        "-shortest",

        str(OUTPUT),
    ]


    run_ffmpeg(
        command
    )


def inspect_output() -> None:

    if not OUTPUT.exists():

        raise RuntimeError(
            "FFmpeg finished, "
            "but output.mp4 was not created."
        )


    size =
        OUTPUT.stat().st_size


    if size <= 0:

        raise RuntimeError(
            "output.mp4 was created "
            "but is empty."
        )


    print(
        "SUCCESS:"
    )

    print(
        OUTPUT
    )

    print(
        f"SIZE: {size} bytes"
    )


def main() -> None:

    print(
        "=== Validate input ==="
    )

    validate_inputs()


    print(
        "=== Render ==="
    )

    render()


    print(
        "=== Inspect output ==="
    )

    inspect_output()


if __name__ == "__main__":

    main()
