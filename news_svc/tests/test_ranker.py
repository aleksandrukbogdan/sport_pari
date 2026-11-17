from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.recommendations.evaluate import temporal_recall
from app.recommendations.model import Interaction, NewsRanker


def article(news_id, text, now, **kwargs):
    return SimpleNamespace(
        id=news_id,
        title=text,
        body=text,
        sport_id="football",
        team_ids=[],
        published_at=now - timedelta(hours=1),
        **kwargs,
    )


def test_content_uses_past_events_and_ignores_future_events():
    now = datetime.now(UTC)
    articles = [
        article(1, "Спартак форвард трансфер", now),
        article(2, "Спартак форвард контракт", now),
        article(3, "Теннис турнир корт", now),
    ]
    events = [
        Interaction("reader", 1, "comment", now),
        Interaction("reader", 3, "view", now + timedelta(days=1)),
    ]
    ranker = NewsRanker()
    ranker.fit(articles, events, as_of=now)
    results = ranker.rank("reader", articles)
    assert [r.news_id for r in results] == [2, 3, 1]
    assert results[0].content > 0
    assert results[1].content == 0
    assert results[1].popularity == 0
    assert results[2].popularity == 3
    assert results[0].reason == "content"


def test_teams_empty_vocabulary_and_half_life():
    now = datetime.now(UTC)
    articles = [article(1, "!!!", now), article(2, "???", now)]
    articles[0].team_ids = ["cska"]
    ranker = NewsRanker()
    ranker.fit(
        articles,
        [Interaction("other", 2, "view", now - timedelta(hours=36))],
        as_of=now,
    )
    results = ranker.rank("new", articles, team_ids=["cska"])
    assert results[0].news_id == 1
    assert results[0].sport == 1
    assert results[1].popularity == pytest.approx(0.5)


def test_temporal_recall_uses_unseen_holdout_targets():
    now = datetime.now(UTC)
    articles = [
        article(1, "Спартак футбол", now),
        article(2, "Спартак футбол матч", now),
    ]
    events = [
        Interaction("reader", 1, "view", now - timedelta(minutes=1)),
        Interaction("reader", 2, "view", now + timedelta(minutes=1)),
    ]
    report = temporal_recall(articles, events, now, k=1)
    assert report["recall_at_k"] == 1
    assert report["users"] == 1
    assert temporal_recall(articles, [], now)["recall_at_k"] is None
