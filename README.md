So what I want to build is an AI news aggregator where I can take multiple sources. So for example, YouTube channels. And I want, for example, blog posts from OpenAI and Emtropic. And I want to scrape those, put them into a database where we have some kind of structure where we have sources, we have, let's call them articles. And then what I want to do is I want to run a daily digest where we're going to take all of the articles from within the timeframe, and we're going to do an LLM summary around that. And then based on the user insights that we specify in some kind of like agent system prompt, we can generate a daily digest, which is going to be short snippets with a link to the original source. Now from the YouTube channels, I want to be able to create a list of channels. And then we want to get the latest videos from those channels. I think we can use the YouTube RSS feed for that. For the blog posts, we can just have URLs that we can scrape for that. Okay, so I want everything built in a Python backend. I want to use a PostgreSQL database. I want to use SQLAlchemy in order to define the database models and then to also create the tables. I want the project structure to be an app folder where all of the app logic is in. And then I also want a Docker folder where we first create a very minimal setup And then that will probably be starting point. We want to make sure that later down the line, we can easily deploy the whole app to render and then also schedule it every 24 hours to run the reports, get everything. And then when we've created the daily digest, I want to send an email to my personal inbox with this. So that's what I have in mind. I think that would be pretty cool to build.


https://openai.com/news/

https://www.anthropic.com/engineering

https://www.anthropic.com/research

## YouTube surface

The first ingestion surface accepts canonical YouTube channel IDs (`UC...`),
`/channel/UC...` URLs, and handle URLs such as
`https://www.youtube.com/@daveebbelaar`. Handle URLs are first fetched to
resolve their canonical channel ID, then queried through YouTube's Atom feed:

```text
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

It exposes the latest videos for a channel (currently up to 15 entries). The
CLI filters those entries by publication time and fetches English transcripts
by default through `youtube-transcript-api`:

```powershell
uv run python main.py UC1234567890123456789012 --hours 24
uv run python main.py https://www.youtube.com/channel/UC1234567890123456789012 --language en --language de
```

Transcript availability depends on whether the video exposes captions. Handle
resolution requires the channel page to expose its canonical `UC...` ID.

The Python API is exposed through `YouTubeScraper`, which provides
`resolve_channel_id`, `fetch_recent_videos`, `get_transcript`, and
`fetch_recent_videos_with_transcripts` methods. The existing module-level
functions remain available as compatibility wrappers.

## Local PostgreSQL

Copy `example.environment.env` to `.env`, then start PostgreSQL:

```powershell
Copy-Item example.environment.env .env
docker compose --env-file .env -f docker\docker-compose.yml up -d
```

Create the tables after the database is healthy:

```powershell
uv run python -m app.database.create_tables
```

Run all configured scrapers and persist their results:

```powershell
uv run python -c "from app.services.runner import run_scrapers; results = run_scrapers(); print({key: len(value) for key, value in results.items()})"
```

The runner uses a 24-hour lookback by default. Pass `hours=168` for the
previous seven days.

After ingestion, enrich stored Anthropic articles with Markdown and YouTube
videos with transcripts:

```powershell
uv run python -c "from app.services.enrich import enrich_articles; print(enrich_articles())"
```

Or run both stages together:

```powershell
uv run python -c "from app.services.runner import run_pipeline; print(run_pipeline())"
```

Create digests for stored articles that do not have one:

```powershell
uv run python -c "from app.services.process_digest import process_digests; print(process_digests())"
```

The digest processor stores one digest per article in the `digests` table and
uses the article's extracted Markdown, transcript, or RSS description as its
input.