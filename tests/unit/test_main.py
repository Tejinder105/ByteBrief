from unittest.mock import patch

import main
from app.models import ChannelVideo


def test_main_reports_when_no_recent_videos(capsys) -> None:
    with (
        patch("main.fetch_recent_videos_with_transcripts", return_value=[]),
        patch("sys.argv", ["main.py", "UC1234567890123456789012", "--hours", "24"]),
    ):
        main.main()

    assert "No videos found in the last 24 hours" in capsys.readouterr().out


def test_main_prints_channel_video_json(capsys) -> None:
    video = ChannelVideo(
        title="Example",
        url="https://www.youtube.com/watch?v=video-123",
        video_id="video-123",
        published_at="2026-10-25T10:00:00Z",
        description="Description",
        transcript=None,
    )
    with (
        patch("main.fetch_recent_videos_with_transcripts", return_value=[video]),
        patch("sys.argv", ["main.py", "UC1234567890123456789012"]),
    ):
        main.main()

    output = capsys.readouterr().out
    assert '"title": "Example"' in output
    assert '"video_id": "video-123"' in output
    assert '"transcript": null' in output
