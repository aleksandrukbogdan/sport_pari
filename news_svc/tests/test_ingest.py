from datetime import UTC, datetime

import httpx
import pytest
from defusedxml.common import DefusedXmlException
from sqlalchemy import func, select

from app.db import SessionLocal
from app.ingest import import_sources, parse_feed
from app.news.models import News

FEED = b"""<rss><channel><title>Sports feed</title><item><title>A real headline</title><description>&lt;b&gt;Excerpt&lt;/b&gt;</description><link>https://example.org/article?tracking=1</link><pubDate>Fri, 13 Nov 2026 10:00:00 GMT</pubDate></item><item><title>Bad URL</title><link>javascript:alert(1)</link></item></channel></rss>"""


def test_feed_sanitizes_markup_and_urls():
    articles = parse_feed(FEED, "football", datetime(2026, 11, 15, tzinfo=UTC))
    assert len(articles) == 1
    assert articles[0]["summary"] == "Excerpt"
    assert articles[0]["source_url"] == "https://example.org/article"
    assert parse_feed(FEED, "football", datetime(2026, 11, 1, tzinfo=UTC)) == []
    with pytest.raises(DefusedXmlException):
        parse_feed(
            b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss>&xxe;</rss>',
            "football",
        )


async def test_import_is_idempotent_and_failed_source_does_not_erase_data(client):
    def respond(request):
        return (
            httpx.Response(503)
            if request.url.path == "/bad"
            else httpx.Response(200, content=FEED)
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        first = await import_sources(http, {"football": "http://feed/ok"})
        second = await import_sources(
            http, {"football": "http://feed/ok", "hockey": "http://feed/bad"}
        )
    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["existing"] == 1
    assert "hockey" in second["errors"]
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(News)) == 1


def test_espn_import_keeps_metadata_and_excludes_promotional_articles():
    import json

    from app.ingest import parse_espn

    article = {
        "headline": "NHL match report",
        "description": "<b>Three goals</b>",
        "published": "2026-11-13T10:00:00Z",
        "links": {"web": {"href": "https://espn.example/story?id=123&utm_source=feed"}},
        "images": [{"url": "https://images.example/game.jpg"}],
    }
    promo = {**article, "headline": "NHL odds, picks and best bets"}
    rows = parse_espn(
        json.dumps({"articles": [article, promo]}).encode(),
        "hockey",
        datetime(2026, 11, 15, tzinfo=UTC),
    )
    assert len(rows) == 1
    assert rows[0]["body"] == "Three goals"
    assert rows[0]["source_url"] == "https://espn.example/story?id=123"
    assert rows[0]["image_url"] == "https://images.example/game.jpg"
    assert rows[0]["sport_id"] == "hockey"
    assert rows[0]["source_name"] == "ESPN"
