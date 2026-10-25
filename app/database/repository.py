"""Repository operations for scraped sources and articles."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Self

from sqlalchemy import select

from app.database.connection import get_session
from app.database.models import Article, Digest, Source
from app.models import AnthropicArticle, ChannelVideo, OpenAIArticle


class Repository:
    """Persist scraped source records and articles."""

    def __init__(self) -> None:
        self.session = get_session()

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.session.close()

    def _source(self, key: str, name: str, source_type: str, url: str | None) -> Source:
        source = self.session.scalar(select(Source).where(Source.key == key))
        if source is None:
            source = Source(key=key, name=name, source_type=source_type, url=url)
            self.session.add(source)
            self.session.flush()
        return source

    def _save_article(
        self,
        source: Source,
        *,
        external_id: str,
        title: str,
        url: str,
        description: str,
        published_at,
        category: str | None = None,
        content: str | None = None,
        transcript: str | None = None,
    ) -> Article:
        article = self.session.scalar(
            select(Article).where(
                Article.source_id == source.id,
                Article.external_id == external_id,
            )
        )
        if article is None:
            article = Article(
                source=source,
                external_id=external_id,
                title=title,
                url=url,
                description=description,
                published_at=published_at,
            )
            self.session.add(article)

        article.title = title
        article.url = url
        article.description = description
        article.category = category
        article.published_at = published_at
        if content is not None:
            article.content = content
        if transcript is not None:
            article.transcript = transcript
        return article

    def save_youtube_videos(self, videos: Iterable[ChannelVideo]) -> int:
        saved = 0
        for video in videos:
            source = self._source(
                "youtube",
                "YouTube",
                "youtube",
                "https://www.youtube.com/",
            )
            self._save_article(
                source,
                external_id=video.video_id,
                title=video.title,
                url=video.url,
                description=video.description,
                published_at=video.published_at,
                transcript=video.transcript,
            )
            saved += 1
        self.session.commit()
        return saved

    def save_openai_articles(self, articles: Iterable[OpenAIArticle]) -> int:
        return self._save_feed_articles(
            "openai",
            "OpenAI",
            "https://openai.com/news/",
            articles,
        )

    def save_anthropic_articles(self, articles: Iterable[AnthropicArticle]) -> int:
        return self._save_feed_articles(
            "anthropic",
            "Anthropic",
            "https://www.anthropic.com/",
            articles,
        )

    def _save_feed_articles(self, key, name, url, articles) -> int:
        source = self._source(key, name, key, url)
        saved = 0
        for article in articles:
            self._save_article(
                source,
                external_id=article.guid,
                title=article.title,
                url=article.url,
                description=article.description,
                published_at=article.published_at,
                category=article.category,
            )
            saved += 1
        self.session.commit()
        return saved

    def get_articles_without_content(self, source_key: str) -> list[Article]:
        """Return articles for a source that have no extracted content."""

        return list(
            self.session.scalars(
                select(Article)
                .join(Article.source)
                .where(
                    Source.key == source_key,
                    Article.content.is_(None),
                )
                .order_by(Article.published_at.desc())
            )
        )

    def get_articles_without_transcript(self) -> list[Article]:
        """Return YouTube articles that have no transcript."""

        return list(
            self.session.scalars(
                select(Article)
                .join(Article.source)
                .where(
                    Source.key == "youtube",
                    Article.transcript.is_(None),
                )
                .order_by(Article.published_at.desc())
            )
        )

    def update_content(self, article: Article, content: str) -> None:
        """Store extracted article content."""

        article.content = content
        self.session.commit()

    def update_transcript(self, article: Article, transcript: str) -> None:
        """Store an extracted YouTube transcript."""

        article.transcript = transcript
        self.session.commit()

    def get_articles_without_digest(self) -> list[Article]:
        """Return articles that have not been summarized yet."""

        return list(
            self.session.scalars(
                select(Article)
                .outerjoin(Article.digest)
                .where(Digest.id.is_(None))
                .order_by(Article.published_at.desc())
            )
        )

    def save_digest(
        self,
        article: Article,
        *,
        title: str,
        summary: str,
    ) -> Digest:
        """Create a digest linked to an article."""

        digest = Digest(
            article=article,
            url=article.url,
            title=title,
            summary=summary,
        )
        self.session.add(digest)
        self.session.commit()
        return digest
