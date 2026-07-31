"""Write a quick technical inventory of video files without modifying sources."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    videos = sorted(args.folder.rglob("*.mp4"))
    rows = []
    for path in videos:
        capture = cv2.VideoCapture(str(path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 0
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.release()
        match = re.search(r"(20\d{2}\.\d{2}\.\d{2})", path.name)
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "date": match.group(1) if match else "unknown",
                "seconds": round(frames / fps if fps else 0, 2),
                "size_mb": round(path.stat().st_size / 1048576, 1),
                "resolution": f"{width}x{height}",
                "fps": round(fps, 2),
            }
        )
    result = {
        "count": len(rows),
        "total_gb": round(sum(path.stat().st_size for path in videos) / 1073741824, 2),
        "total_minutes": round(sum(row["seconds"] for row in rows) / 60, 1),
        "by_date": dict(sorted(Counter(row["date"] for row in rows).items())),
        "duration_min": min((row["seconds"] for row in rows), default=0),
        "duration_max": max((row["seconds"] for row in rows), default=0),
        "rows": rows,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
