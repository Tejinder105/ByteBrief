from unittest.mock import patch

from app.services.enrich import enrich_articles


def test_enrich_articles_runs_both_stages() -> None:
    anthropic_result = {"total": 1, "processed": 1, "failed": 0}
    youtube_result = {
        "total": 2,
        "processed": 1,
        "unavailable": 1,
        "failed": 0,
    }
    with (
        patch(
            "app.services.enrich.process_anthropic_content",
            return_value=anthropic_result,
        ),
        patch(
            "app.services.enrich.process_youtube_transcripts",
            return_value=youtube_result,
        ),
    ):
        result = enrich_articles()

    assert result == {
        "anthropic": anthropic_result,
        "youtube": youtube_result,
    }
