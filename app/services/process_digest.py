"""Create and persist digests for stored articles."""

from __future__ import annotations

import logging

from app.agent.digest import DigestAgent
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def process_digests() -> dict[str, int]:
    """Summarize every stored article that does not have a digest."""

    processed = 0
    failed = 0
    with Repository() as repository:
        articles = repository.get_articles_without_digest()
        agent = DigestAgent()
        for article in articles:
            try:
                content = article.content or article.transcript or article.description
                if not content.strip():
                    failed += 1
                    logger.warning("Article %s has no content to summarize", article.id)
                    continue
                digest = agent.generate(title=article.title, content=content)
                repository.save_digest(
                    article,
                    title=digest.title,
                    summary=digest.summary,
                )
                processed += 1
            except Exception:
                repository.session.rollback()
                failed += 1
                logger.exception("Failed to create digest for article %s", article.id)
    return {"total": len(articles), "processed": processed, "failed": failed}
