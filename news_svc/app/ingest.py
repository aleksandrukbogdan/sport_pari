"""Import attributed sports RSS and ESPN news excerpts with python -m app.ingest."""

import argparse
import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import settings
from app.db import SessionLocal, engine
from app.news.models import News

logger = logging.getLogger(__name__)
MEDIA = "{http://search.yahoo.com/mrss/}"
PROMOTIONAL_CONTENT = re.compile(
    r"\b(?:best bets?|betting|sportsbook|parlays?|promo codes?|moneyline|fantasy (?:basketball|hockey))\b"
    r"|\bodds\b.*\bpicks\b|\b(?:NBA|NHL|NFL) odds\b",
    re.IGNORECASE,
)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _Text()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def source_url(value: str, *, canonical: bool = False) -> str | None:
    try:
        url = urlsplit(value.strip())
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
        ):
            return None
        query = url.query
        if canonical:
            query = urlencode(
                [
                    (name, value)
                    for name, value in parse_qsl(query, keep_blank_values=True)
                    if not name.lower().startswith("utm_")
                    and name.lower()
                    not in ("tracking", "at_medium", "at_campaign", "at_link_origin")
                ]
            )
        result = urlunsplit((url.scheme, url.netloc, url.path, query, ""))
        return result if len(result) <= 2048 else None
    except ValueError:
        return None


def parse_feed(
    content: bytes, sport_id: str, now: datetime | None = None
) -> list[dict]:
    root = ElementTree.fromstring(content)
    source_name = plain_text(root.findtext("./channel/title", "RSS"))[:100]
    articles = {}
    for item in root.findall("./channel/item")[:200]:
        title = plain_text(item.findtext("title", ""))[:300]
        excerpt = plain_text(item.findtext("description", ""))[:500]
        link = source_url(item.findtext("link", ""), canonical=True)
        if not title or not link or PROMOTIONAL_CONTENT.search(title):
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
        except (TypeError, ValueError, OverflowError):
            continue
        if published > (now or datetime.now(UTC)):
            continue
        image = None
        for element in list(item):
            if element.tag in (MEDIA + "thumbnail", MEDIA + "content") or (
                element.tag == "enclosure"
                and element.get("type", "").startswith("image/")
            ):
                image = source_url(element.get("url", ""))
                if image:
                    break
        articles[link] = {
            "title": title,
            "summary": excerpt,
            "body": excerpt or title,
            "sport_id": sport_id,
            "team_ids": [],
            "source_url": link,
            "source_name": source_name,
            "image_url": image,
            "published_at": published,
        }
    return list(articles.values())


def parse_espn(
    content: bytes, sport_id: str, now: datetime | None = None
) -> list[dict]:
    payload = json.loads(content)
    articles = {}
    for item in payload.get("articles", [])[:200]:
        title = plain_text(item.get("headline", ""))[:300]
        excerpt = plain_text(item.get("description", ""))[:500]
        link = source_url(
            item.get("links", {}).get("web", {}).get("href", ""), canonical=True
        )
        try:
            published = datetime.fromisoformat(item.get("published", ""))
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
        except ValueError:
            continue
        if (
            not title
            or not link
            or PROMOTIONAL_CONTENT.search(title)
            or published > (now or datetime.now(UTC))
        ):
            continue
        images = item.get("images", [])
        image = source_url(images[0].get("url", "")) if images else None
        articles[link] = {
            "title": title,
            "summary": excerpt,
            "body": excerpt or title,
            "sport_id": sport_id,
            "team_ids": [],
            "source_url": link,
            "source_name": "ESPN",
            "image_url": image,
            "published_at": published,
        }
    return list(articles.values())


async def _fetch(http, sport_id, url, semaphore):
    async with semaphore:
        try:
            async with http.stream("GET", url) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 2_000_000:
                        raise ValueError("News source exceeds 2 MB")
            parser = parse_espn if content.lstrip().startswith(b"{") else parse_feed
            return sport_id, url, parser(bytes(content), sport_id), None
        except (
            httpx.HTTPError,
            ValueError,
            ParseError,
            DefusedXmlException,
            TypeError,
            AttributeError,
        ) as error:
            logger.warning("News fetch failed for %s at %s: %s", sport_id, url, error)
            return sport_id, url, [], str(error)


async def import_sources(
    http: httpx.AsyncClient, sources: dict[str, str | list[str]]
) -> dict:
    report = {"inserted": 0, "existing": 0, "errors": {}, "by_sport": {}}
    semaphore = asyncio.Semaphore(4)
    fetched = await asyncio.gather(
        *[
            _fetch(http, sport_id, url, semaphore)
            for sport_id, urls in sources.items()
            for url in ([urls] if isinstance(urls, str) else urls)
        ]
    )
    for sport_id, url, articles, error in fetched:
        if error is not None:
            report["errors"].setdefault(sport_id, []).append(
                {"url": url, "error": error}
            )
            continue
        counts = {"inserted": 0, "existing": 0}
        try:
            async with SessionLocal.begin() as session:
                insert = (
                    sqlite_insert
                    if session.get_bind().dialect.name == "sqlite"
                    else pg_insert
                )
                for values in articles:
                    stmt = (
                        insert(News)
                        .values(**values)
                        .on_conflict_do_nothing(index_elements=["source_url"])
                        .returning(News.id)
                    )
                    created = await session.scalar(stmt)
                    counts["inserted" if created is not None else "existing"] += 1
                    if created is None and values["image_url"]:
                        await session.execute(
                            update(News)
                            .where(
                                News.source_url == values["source_url"],
                                News.image_url.is_(None),
                            )
                            .values(image_url=values["image_url"])
                        )
            sport_report = report["by_sport"].setdefault(
                sport_id, {"inserted": 0, "existing": 0}
            )
            for name, count in counts.items():
                report[name] += count
                sport_report[name] += count
        except Exception as error:
            logger.exception("News persistence failed for %s", sport_id)
            report["errors"].setdefault(sport_id, []).append(
                {"url": url, "error": str(error)}
            )
    return report


async def run(interval: int):
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "sport-pari-news/1.0 news reader"},
        ) as http:
            while True:
                report = await import_sources(http, settings.news_sources)
                print(json.dumps(report, ensure_ascii=False), flush=True)
                if not interval:
                    if report["errors"]:
                        raise SystemExit(1)
                    return
                await asyncio.sleep(interval)
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Seconds between imports, 0 imports once",
    )
    args = parser.parse_args()
    if args.interval and args.interval < 60:
        parser.error("interval must be zero or at least 60 seconds")
    asyncio.run(run(args.interval))


if __name__ == "__main__":
    main()
