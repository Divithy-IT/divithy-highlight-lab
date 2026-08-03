"""Create context-safe gaming episode drafts from a package of source clips.

The selector ranks movement and audio activity but keeps a configurable lead-in
before the peak, so a spoken setup and the action's payoff stay together.
Source files are only read; all artefacts are written to the output folder.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from tqdm import tqdm


SAMPLE_HZ = 2.0


def normalise(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    low, high = np.percentile(values, [10, 90])
    if high <= low + 1e-9:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - low) / (high - low), 0, 1).astype(np.float32)


def audio_energy(path: Path, sample_count: int) -> np.ndarray:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
    try:
        raw = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    except subprocess.CalledProcessError:
        return np.zeros(sample_count, dtype=np.float32)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return np.zeros(sample_count, dtype=np.float32)
    pieces = np.array_split(samples, sample_count)
    return np.array([np.sqrt(np.mean(piece * piece)) if piece.size else 0 for piece in pieces], dtype=np.float32)


def analyse_clip(
    path: Path,
    segment_seconds: float,
    lead_seconds: float,
    adaptive_end_window_seconds: float = 0.0,
) -> dict:
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frames / fps if frames > 0 else segment_seconds
    interval = max(1, int(round(fps / SAMPLE_HZ)))
    motion: list[float] = []
    previous = None
    index = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if index % interval == 0:
            ok, frame = cap.retrieve()
            if not ok:
                index += 1
                continue
            frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            motion.append(0.0 if previous is None else float(cv2.absdiff(gray, previous).mean()))
            previous = gray
        index += 1
    cap.release()
    motion_array = np.asarray(motion, dtype=np.float32)
    sound = audio_energy(path, len(motion_array))
    score = 0.65 * normalise(motion_array) + 0.35 * normalise(sound)
    # A 12-second activity score locates an event; the final selection carries
    # considerably more lead-in and aftermath for dialogue and context.
    event_window = max(1, int(round(12 * SAMPLE_HZ)))
    smooth = np.convolve(score, np.ones(event_window, dtype=np.float32) / event_window, mode="same")
    centre = int(np.argmax(smooth)) if smooth.size else 0
    start = max(0.0, centre / SAMPLE_HZ - lead_seconds)
    if duration > segment_seconds:
        start = min(start, duration - segment_seconds)
    clip_duration = min(segment_seconds, max(1.0, duration - start))
    # Avoid cutting a sentence or firefight at a rigid timestamp. Search only
    # near the requested ending so the total episode length stays predictable.
    if adaptive_end_window_seconds > 0 and duration - start > segment_seconds:
        earliest = max(1.0, segment_seconds - 2 * adaptive_end_window_seconds)
        latest = min(duration - start, segment_seconds + adaptive_end_window_seconds)
        first = max(0, int(round((start + earliest) * SAMPLE_HZ)))
        last = min(len(score), int(round((start + latest) * SAMPLE_HZ)) + 1)
        if last > first:
            quiet_window = max(1, int(round(1.5 * SAMPLE_HZ)))
            quietness = np.convolve(
                score, np.ones(quiet_window) / quiet_window, mode="same"
            )
            boundary = first + int(np.argmin(quietness[first:last]))
            clip_duration = min(duration - start, boundary / SAMPLE_HZ - start)
    return {
        "file": path.name,
        "path": str(path),
        "source_duration_seconds": round(float(duration), 2),
        "selected_start_seconds": round(float(start), 2),
        "selected_duration_seconds": round(float(clip_duration), 2),
        "peak_score": round(float(smooth[centre]) if smooth.size else 0.0, 3),
        "selector_version": "context-v2",
    }


def brand_row(path: Path, kind: str) -> dict:
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS) or 60.0
    frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    capture.release()
    duration = frames / fps if frames else 4.0
    return {"file": path.name, "path": str(path), "source_duration_seconds": round(duration, 2), "selected_start_seconds": 0.0,
            "selected_duration_seconds": round(duration, 2), "peak_score": None, "selector_version": kind}


def render_video(rows: list[dict], destination: Path, video_encoder: str) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y"]
    for row in rows:
        command += ["-ss", str(row["selected_start_seconds"]), "-t", str(row["selected_duration_seconds"]), "-i", row["path"]]
    filters, parts = [], []
    for index, _ in enumerate(rows):
        filters.append(f"[{index}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60,setsar=1,setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[{index}:a]aresample=48000,asetpts=PTS-STARTPTS[a{index}]")
        parts.append(f"[v{index}][a{index}]")
    filters.append("".join(parts) + f"concat=n={len(rows)}:v=1:a=1[v][aconcat]")
    # Keep dialogue intelligible and prevent sudden screams/game peaks from
    # becoming painfully loud. EBU-style target with a true-peak safety limit.
    filters.append("[aconcat]loudnorm=I=-16:LRA=11:TP=-1.5,alimiter=limit=0.891[a]")
    video_options = (
        ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
        if video_encoder == "h264_nvenc"
        else ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    )
    command += [
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        *video_options, "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(destination),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--segment-seconds", type=float, default=34.0)
    parser.add_argument("--lead-seconds", type=float, default=10.0)
    parser.add_argument(
        "--adaptive-end-window-seconds",
        type=float,
        default=0.0,
        help="Move the ending to a quieter point near the target duration.",
    )
    parser.add_argument(
        "--max-clips",
        type=int,
        help="Keep only the strongest clips, then restore chronological order.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional text file with one absolute source-video path per line.",
    )
    parser.add_argument(
        "--pinned-manifest",
        type=Path,
        help="Optional text file of source paths that must stay in the episode.",
    )
    parser.add_argument("--exclude", action="append", default=[], help="Exact source file name to omit")
    parser.add_argument("--intro", type=Path)
    parser.add_argument("--outro", type=Path)
    parser.add_argument("--title", default="episode")
    parser.add_argument(
        "--video-encoder",
        choices=["libx264", "h264_nvenc"],
        default="libx264",
    )
    args = parser.parse_args()
    if args.manifest:
        clips = [
            Path(line.strip())
            for line in args.manifest.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        missing = [path for path in clips if not path.is_file()]
        if missing:
            raise SystemExit(f"Manifest references missing source: {missing[0]}")
    else:
        clips = sorted(path for path in args.source.rglob("*.mp4"))
    clips = [path for path in clips if path.name not in set(args.exclude)]
    if not clips:
        raise SystemExit("No MP4 clips remain after exclusions.")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = [
        analyse_clip(
            clip,
            args.segment_seconds,
            args.lead_seconds,
            args.adaptive_end_window_seconds,
        )
        for clip in tqdm(clips, desc="Analysing clips")
    ]
    pinned_paths: set[str] = set()
    if args.pinned_manifest:
        pinned_paths = {
            str(Path(line.strip()).resolve())
            for line in args.pinned_manifest.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        }
    if args.max_clips is not None and args.max_clips < len(rows):
        # Large packages otherwise create episodes that overstay their welcome.
        # Rank by detected activity, but return to recording order for a natural
        # story flow rather than a random best-of sequence.
        pinned = [row for row in rows if str(Path(row["path"]).resolve()) in pinned_paths]
        if len(pinned) > args.max_clips:
            raise SystemExit("There are more pinned clips than --max-clips.")
        pinned_set = {row["path"] for row in pinned}
        ranked_remaining = sorted(
            (row for row in rows if row["path"] not in pinned_set),
            key=lambda row: float(row["peak_score"]),
            reverse=True,
        )
        rows = sorted(pinned + ranked_remaining[:args.max_clips - len(pinned)], key=lambda row: row["path"])
    with (args.output / "wybrane_momenty.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "wybrane_momenty.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    notes = [
        "selector=context-v3",
        f"segment_seconds={args.segment_seconds}",
        f"lead_seconds={args.lead_seconds}",
        f"adaptive_end_window_seconds={args.adaptive_end_window_seconds}",
        f"max_clips={args.max_clips or 'all'}",
        f"pinned_clips={len(pinned_paths)}",
        *[f"excluded={name}" for name in args.exclude],
    ]
    (args.output / "selection_notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
    render_rows = rows.copy()
    if args.intro:
        render_rows.insert(0, brand_row(args.intro, "brand-intro"))
    if args.outro:
        render_rows.append(brand_row(args.outro, "brand-outro"))
    render_video(render_rows, args.output / f"{args.title}.mp4", args.video_encoder)


if __name__ == "__main__":
    main()
