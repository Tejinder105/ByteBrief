"""Generate structured article digests with OpenAI."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


class DigestOutput(BaseModel):
    """Structured summary returned by the digest agent."""

    title: str = Field(description="A concise title for the article digest.")
    summary: str = Field(
        description="A factual summary in two or three sentences."
    )


class DigestAgent:
    """Create concise, factual summaries for stored articles."""

    model = "gpt-4.1-mini"

    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(self, *, title: str, content: str) -> DigestOutput:
        """Generate a structured digest from an article title and content."""

        response = self.client.responses.parse(
            model=self.model,
            instructions=(
                "You summarize AI news for a technical reader. "
                "Create a concise, factual title and a two or three sentence "
                "summary. Focus on what happened, the important details, and "
                "why it matters. Do not invent facts or use marketing language."
            ),
            input=f"Article title:\n{title}\n\nArticle content:\n{content[:12000]}",
            text_format=DigestOutput,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI returned no structured digest")
        return response.output_parsed
