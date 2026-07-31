"""Find Polish profanity with Whisper and optionally replace it with a soft beep.

The source video is never modified.  The default command only writes a review
report; pass --render after checking the detected words and timestamps.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import imageio_ffmpeg
from faster_whisper import WhisperModel


STRONG_PATTERNS = (
    r"(?:za|na|wy|po|do|prze|od|roz|u|o)?jeb\w*",
    r"(?:s|wy|prze|na|po|do)?kurw\w*",
    r"(?:s|wy|prze|na|po|do)?pierd\w*",
    r"(?:s|wy|prze|na|po|do)?chuj\w*",
    r"(?:s|wy|prze|na|po|do)?kutas\w*",
    r"(?:s|wy|prze|na|po|do)?dziwk\w*",
    r"(?:s|wy|prze|na|po|do)?cwel\w*",
)

MILD_WORDS = {
    "cholera",
    "kurde",
    "kurczę",
    "kurcze",
    "dupa",
    "dupy",
    "gówno",
    "gowno",
    "shit",
    "damn",
}


@dataclass
class Hit:
    start: float
    end: float
    word: str
    level: str
    probability: float


def normalise_word(text: str) -> str:
    return re.sub(r"[^a-ząćęłńóśźż]", "", text.casefold())


def classify(text: str) -> str | None:
    word = normalise_word(text)
    if not word:
        return None
    if word in MILD_WORDS:
        return "mild"
    if any(re.fullmatch(pattern, word) for pattern in STRONG_PATTERNS):
        return "strong"
    return None


def transcribe(video: Path, model_name: str, device: str) -> tuple[list[Hit], dict]:
    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(video),
        language="pl",
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=True,
    )
    hits: list[Hit] = []
    transcript: list[dict] = []
    for segment in segments:
        words = []
        for word in segment.words or []:
            words.append(
                {
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                    "word": word.word.strip(),
                    "probability": round(float(word.probability), 3),
                }
            )
            level = classify(word.word)
            if level:
                # A small margin hides consonants left at either edge.
                hits.append(
                    Hit(
                        start=max(0.0, float(word.start) - 0.07),
                        end=float(word.end) + 0.09,
                        word=word.word.strip(),
                        level=level,
                        probability=float(word.probability),
                    )
                )
        transcript.append(
            {
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": segment.text.strip(),
                "words": words,
            }
        )
    metadata = {
        "language": info.language,
        "language_probability": round(float(info.language_probability), 3),
        "duration": round(float(info.duration), 3),
        "segments": transcript,
    }
    return hits, metadata


def selected_hits(hits: list[Hit], mode: str) -> list[Hit]:
    if mode == "strict":
        return hits
    # Balanced mode leaves ordinary mild expressions alone, except in the
    # opening where a clean first impression is useful.
    return [hit for hit in hits if hit.level == "strong" or hit.start < 15.0]


def condition(hits: list[Hit]) -> str:
    return "+".join(f"between(t,{hit.start:.3f},{hit.end:.3f})" for hit in hits) or "0"


def render(video: Path, output: Path, hits: list[Hit]) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    expr = condition(hits)
    duration = max(hit.end for hit in hits) + 1.0
    filters = (
        f"[0:a]volume='if(gt({expr},0),0,1)'[clean];"
        f"sine=frequency=880:sample_rate=48000:duration={duration:.3f},"
        f"volume='if(gt({expr},0),0.10,0)'[beep];"
        "[clean][beep]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[aout]"
    )
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video),
        "-filter_complex",
        filters,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Polish gaming profanity detector and bleeper")
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", default="small", help="Whisper model (default: small)")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--mode", choices=("balanced", "strict"), default="balanced")
    parser.add_argument("--render", action="store_true", help="Create a censored MP4 after analysis")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.is_file():
        raise SystemExit(f"Video not found: {video}")
    report_dir = video.parent / "analiza_cenzury"
    report_dir.mkdir(exist_ok=True)
    hits, transcript = transcribe(video, args.model, args.device)
    chosen = selected_hits(hits, args.mode)
    stem = video.stem

    (report_dir / f"{stem}_transkrypcja.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (report_dir / f"{stem}_przeklenstwa.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("start", "end", "word", "level", "probability", "censored"))
        writer.writeheader()
        chosen_keys = {(hit.start, hit.end, hit.word) for hit in chosen}
        for hit in hits:
            row = asdict(hit)
            row["start"] = round(hit.start, 3)
            row["end"] = round(hit.end, 3)
            row["probability"] = round(hit.probability, 3)
            row["censored"] = (hit.start, hit.end, hit.word) in chosen_keys
            writer.writerow(row)

    print(f"Detected: {len(hits)}; selected for bleeping: {len(chosen)}")
    print(f"Report: {report_dir}")
    if args.render:
        if not chosen:
            print("No selected words; render skipped and source remains unchanged.")
            return
        output = args.output or video.with_name(f"{stem}_CENZURA{video.suffix}")
        render(video, output.resolve(), chosen)
        print(f"Censored copy: {output.resolve()}")


if __name__ == "__main__":
    main()
