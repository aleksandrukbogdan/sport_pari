from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.recommendations.features import (
    EVENT_WEIGHT,
    POPULARITY_HALF_LIFE_HOURS,
    W_CONTENT,
    W_POPULARITY,
    W_SPORT,
)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@dataclass(frozen=True)
class Interaction:
    user_id: str
    news_id: int
    event_type: str
    created_at: datetime


@dataclass(frozen=True)
class RankResult:
    news_id: int
    score: float
    reason: str
    seen: bool
    popularity: float
    content: float
    sport: float


class NewsRanker:
    """Fit TF-IDF on published articles and rank using only events before as_of."""

    def fit(
        self,
        articles,
        interactions,
        *,
        as_of: datetime | None = None,
        popularity: dict[int, float] | None = None,
    ) -> None:
        self.as_of = utc(as_of or datetime.now(UTC))
        self.popularity = popularity
        self.articles = [
            a for a in articles if a.published_at and utc(a.published_at) <= self.as_of
        ]
        self.index = {a.id: i for i, a in enumerate(self.articles)}
        self.interactions = [
            e
            for e in interactions
            if utc(e.created_at) <= self.as_of and e.news_id in self.index
        ]
        self.matrix = csr_matrix((len(self.articles), 0))
        texts = [f"{a.title} {a.body}" for a in self.articles]
        if texts:
            vectorizer = TfidfVectorizer(max_features=20000, sublinear_tf=True)
            try:
                self.matrix = vectorizer.fit_transform(texts)
            except ValueError as error:
                if "empty vocabulary" not in str(error):
                    raise

    def rank(
        self, user_id: str, candidates, *, sport_ids=(), team_ids=()
    ) -> list[RankResult]:
        history = np.zeros(len(self.articles))
        popularity = np.zeros(len(self.articles))
        seen = set()
        for event in self.interactions:
            index = self.index[event.news_id]
            hours = (self.as_of - utc(event.created_at)).total_seconds() / 3600
            weight = EVENT_WEIGHT[event.event_type] * 0.5 ** (
                hours / POPULARITY_HALF_LIFE_HOURS
            )
            if self.popularity is None:
                popularity[index] += weight
            if event.user_id == user_id:
                history[index] += weight
                seen.add(event.news_id)
        content = np.zeros(len(self.articles))
        if history.any() and self.matrix.shape[1]:
            profile = csr_matrix(history.reshape(1, -1)) @ self.matrix
            content = cosine_similarity(profile, self.matrix).ravel()
        results = []
        for article in candidates:
            if article.id not in self.index:
                continue
            index = self.index[article.id]
            pop = float(
                self.popularity.get(article.id, 0.0)
                if self.popularity is not None
                else popularity[index]
            )
            text = float(content[index])
            # Team IDs can only match explicit catalog tags, never guessed names.
            sport = float(
                article.sport_id in sport_ids
                or bool(set(article.team_ids or ()) & set(team_ids))
            )
            signals = [
                W_POPULARITY * pop / (1 + pop),
                W_CONTENT * text,
                W_SPORT * sport,
            ]
            score = sum(signals)
            reason = ("popularity", "content", "sport")[int(np.argmax(signals))]
            results.append(
                RankResult(
                    article.id, score, reason, article.id in seen, pop, text, sport
                )
            )
        return sorted(results, key=lambda r: (r.seen, -r.score))
