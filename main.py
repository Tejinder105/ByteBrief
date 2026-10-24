from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from app.scrapers.youtube import fetch_recent_videos_with_transcripts


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Fetch recent YouTube videos and their transcripts."
    )
    parser.add_argument(
        "channels",
        nargs="+",
        help="YouTube UC... channel IDs or /channel/UC... URLs.",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Look back this many hours (default: 24).",
    )
    parser.add_argument(
        "--language",
        action="append",
        dest="languages",
        default=None,
        help="Preferred transcript language; may be repeated (default: en).",
    )
    args = parser.parse_args()

    since = datetime.now(UTC) - timedelta(hours=args.hours)
    videos = fetch_recent_videos_with_transcripts(
        args.channels,
        since=since,
        languages=tuple(args.languages or ["en"]),
    )
    if not videos:
        print(
            f"No videos found in the last {args.hours:g} hours "
            f"(since {since.isoformat()})."
        )
        return

    for video in videos:
        print(video.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
