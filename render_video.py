from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"

PHOTO = INPUT_DIR / "photo.png"
AUDIO = INPUT_DIR / "narration.wav"
SUBTITLE = INPUT_DIR / "subtitle.srt"

OUTPUT = OUTPUT_DIR / "output.mp4"


def run_ffmpeg(command: list[str]) -> None:
    print("Running:")
    print(" ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed with exit code "
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
            + "\n".join(missing)
        )


def render() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        "ffmpeg",
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
        # Video filter
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
        # Fixed duration
        # -----------------------------------------------------
        "-t",
        "15",

        # -----------------------------------------------------
        # Frame rate
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
        # Video
        # -----------------------------------------------------
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        # -----------------------------------------------------
        # Audio
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
        # Do not extend beyond 15 seconds
        # -----------------------------------------------------
        "-shortest",

        str(OUTPUT),
    ]

    run_ffmpeg(command)


def main() -> None:

    validate_inputs()

    render()

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
        f"SUCCESS: {OUTPUT}"
    )

    print(
        f"SIZE: {size} bytes"
    )


if __name__ == "__main__":
    main()
