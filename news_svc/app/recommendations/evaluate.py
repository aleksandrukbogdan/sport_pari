"""Temporal Recall@K on saved interactions, without fitting on holdout events."""

import argparse
import asyncio
import json
from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.news.models import News
from app.recommendations.model import NewsRanker, utc
from app.recommendations.repository import PostgresViewRepository


def temporal_recall(articles, interactions, cutoff: datetime, *, k: int = 10) -> dict:
    if k < 1:
        raise ValueError("k must be positive")
    cutoff = utc(cutoff)
    eligible = [a for a in articles if a.published_at and utc(a.published_at) <= cutoff]
    eligible_ids = {a.id for a in eligible}
    training = [e for e in interactions if utc(e.created_at) <= cutoff]
    ranker = NewsRanker()
    ranker.fit(eligible, training, as_of=cutoff)
    seen = {}
    for event in training:
        seen.setdefault(event.user_id, set()).add(event.news_id)
    targets = {}
    for event in interactions:
        if (
            utc(event.created_at) > cutoff
            and event.news_id in eligible_ids
            and event.news_id not in seen.get(event.user_id, set())
        ):
            targets.setdefault(event.user_id, set()).add(event.news_id)
    recalls = []
    for user, target in targets.items():
        ranked = [r.news_id for r in ranker.rank(user, eligible) if not r.seen][:k]
        recalls.append(len(set(ranked) & target) / len(target))
    return {
        "k": k,
        "cutoff": cutoff.isoformat(),
        "users": len(recalls),
        "recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "eligible_articles": len(eligible),
    }


async def evaluate(cutoff, k):
    try:
        async with SessionLocal() as session:
            articles = list(
                await session.scalars(select(News).order_by(News.published_at.desc()))
            )
            from datetime import UTC

            interactions = await PostgresViewRepository(session).interactions(
                [a.id for a in articles], datetime.now(UTC)
            )
            print(
                json.dumps(
                    temporal_recall(articles, interactions, cutoff, k=k), indent=2
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", required=True, type=datetime.fromisoformat)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    if args.cutoff.tzinfo is None or args.k < 1:
        parser.error("cutoff requires timezone and k must be positive")
    asyncio.run(evaluate(args.cutoff, args.k))
