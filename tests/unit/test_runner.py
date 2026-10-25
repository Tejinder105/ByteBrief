from datetime import UTC
from unittest.mock import patch

import pytest

from app.services.runner import run_pipeline, run_scrapers


def test_run_scrapers_passes_one_lookback_to_all_sources() -> None:
    with (
        patch("app.services.runner.Repository") as repository_class,
        patch("app.services.runner.YouTubeScraper") as youtube_class,
        patch("app.services.runner.OpenAIScraper") as openai_class,
        patch("app.services.runner.AnthropicScraper") as anthropic_class,
    ):
        repository = repository_class.return_value.__enter__.return_value
        youtube = youtube_class.return_value.__enter__.return_value
        openai = openai_class.return_value.__enter__.return_value
        anthropic = anthropic_class.return_value.__enter__.return_value
        youtube.fetch_recent_videos_with_transcripts.return_value = []
        openai.fetch_recent_articles.return_value = []
        anthropic.fetch_recent_articles.return_value = []

        result = run_scrapers(hours=24)

    assert result == {"youtube": [], "openai": [], "anthropic": []}
    repository.save_youtube_videos.assert_called_once_with([])
    repository.save_openai_articles.assert_called_once_with([])
    repository.save_anthropic_articles.assert_called_once_with([])
    since = youtube.fetch_recent_videos_with_transcripts.call_args.kwargs["since"]
    assert since.tzinfo == UTC
    openai.fetch_recent_articles.assert_called_once()
    anthropic.fetch_recent_articles.assert_called_once()
    assert (
        openai.fetch_recent_articles.call_args.kwargs["since"] == since
    )
    assert (
        anthropic.fetch_recent_articles.call_args.kwargs["since"] == since
    )


def test_run_scrapers_rejects_negative_lookback() -> None:
    with pytest.raises(ValueError, match="hours must not be negative"):
        run_scrapers(hours=-1)


def test_run_pipeline_runs_ingestion_then_enrichment() -> None:
    scraped = {"youtube": [], "openai": [], "anthropic": []}
    enriched = {"anthropic": {}, "youtube": {}}
    with (
        patch("app.services.runner.run_scrapers", return_value=scraped) as scrape,
        patch("app.services.runner.enrich_articles", return_value=enriched) as enrich,
    ):
        result = run_pipeline(hours=48)

    scrape.assert_called_once_with(hours=48)
    enrich.assert_called_once_with()
    assert result == {"scraped": scraped, "enriched": enriched}
