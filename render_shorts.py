"""Render vertical gameplay shorts from an episode selection CSV.

Each short keeps the full 16:9 gameplay image visible over a blurred 9:16
background, then appends the reusable Divithy short outro.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._")[:80]


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--outro", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--body-seconds", type=float, default=28)
    parser.add_argument(
        "--filename-prefix",
        default="Short",
        help="Stable upload-friendly prefix, for example Film_05_Zapowiedz",
    )
    parser.add_argument(
        "--video-encoder",
        choices=["libx264", "h264_nvenc"],
        default="libx264",
    )
    parser.add_argument(
        "--brand-label",
        default="DIVITHYツ // L4D2",
        help="Short label displayed in the upper-left corner.",
    )
    args = parser.parse_args()

    with args.csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ranked = sorted(rows, key=lambda row: float(row["peak_score"]), reverse=True)
    picked: list[dict[str, str]] = []
    files_seen: set[str] = set()
    for row in ranked:
        if row["file"] not in files_seen:
            picked.append(row)
            files_seen.add(row["file"])
        if len(picked) == args.count:
            break

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "shorts_selection.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(picked)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    font = "C\\:/Windows/Fonts/YuGothM.ttc"
    for index, row in enumerate(picked, start=1):
        source = Path(row["path"])
        # Keep a little lead-in, while bringing the peak closer to the center.
        start = max(0.0, float(row["selected_start_seconds"]) + 2.0)
        target = args.output / f"{safe_name(args.filename_prefix)}_{index:02d}.mp4"
        filter_graph = (
            "[0:v]split=2[game][bgsrc];"
            "[bgsrc]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:10[bg];"
            # Direct scaling avoids an FFmpeg one-pixel rounding conflict
            # (1080p 16:9 maps to 607.5 pixels high).
            "[game]scale=1080:608[foreground];"
            "[bg][foreground]overlay=0:(H-h)/2,"
            f"drawtext=fontfile='{font}':text='{args.brand_label}':"
            "fontcolor=0xEAFBFF:fontsize=35:x=40:y=58:borderw=2:"
            "bordercolor=0x00D9FF@0.70:shadowcolor=0x6B1EFF:"
            "shadowx=3:shadowy=3,setsar=1,setpts=PTS-STARTPTS[v0];"
            "[0:a]aresample=48000,asetpts=PTS-STARTPTS[a0];"
            "[1:v]setsar=1,setpts=PTS-STARTPTS[v1];"
            "[1:a]aresample=48000,asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][aconcat];"
            "[aconcat]loudnorm=I=-16:LRA=11:TP=-1.5,"
            "alimiter=limit=0.891[a]"
        )
        video_options = (
            ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
            if args.video_encoder == "h264_nvenc"
            else ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]
        )
        command = [
            ffmpeg, "-y",
            "-ss", f"{start:.3f}", "-t", f"{args.body_seconds:.3f}", "-i", str(source),
            "-i", str(args.outro),
            "-filter_complex", filter_graph,
            "-map", "[v]", "-map", "[a]",
            *video_options,
            "-r", "60", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(target),
        ]
        print(f"[{index}/{len(picked)}] {source.name} @ {start:.1f}s")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    run()
