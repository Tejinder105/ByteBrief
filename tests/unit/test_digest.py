from unittest.mock import Mock, patch

from app.agent.digest import DigestAgent, DigestOutput
from app.services.process_digest import process_digests


def test_digest_agent_uses_structured_responses_api() -> None:
    client = Mock()
    client.responses.parse.return_value.output_parsed = DigestOutput(
        title="A concise title",
        summary="First sentence. Second sentence.",
    )

    result = DigestAgent(client=client).generate(
        title="Original title",
        content="Article content",
    )

    assert result.title == "A concise title"
    client.responses.parse.assert_called_once()
    call = client.responses.parse.call_args.kwargs
    assert call["model"] == "gpt-4.1-mini"
    assert call["text_format"] is DigestOutput


def test_process_digests_summarizes_pending_articles() -> None:
    article = Mock(id=1, title="Article", content="Content", transcript=None, description="")
    repository = Mock()
    repository.get_articles_without_digest.return_value = [article]
    digest = DigestOutput(title="Digest title", summary="Two sentences.")
    agent = Mock()
    agent.generate.return_value = digest

    with (
        patch("app.services.process_digest.Repository") as repository_class,
        patch("app.services.process_digest.DigestAgent", return_value=agent),
    ):
        repository_class.return_value.__enter__.return_value = repository
        result = process_digests()

    assert result == {"total": 1, "processed": 1, "failed": 0}
    repository.save_digest.assert_called_once_with(
        article,
        title="Digest title",
        summary="Two sentences.",
    )
