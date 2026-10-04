from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Match, MatchStatus, Outcome, PredictionStatus, UserPrediction


def test_contract_tables_cover_match_copy_and_events() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "matches",
        "user_predictions",
        "notifications",
        "processed_events",
    }

    match_columns = {column["name"]: column for column in inspector.get_columns("matches")}
    assert match_columns["score_home"]["nullable"] is True
    assert match_columns["outcome"]["nullable"] is True
    assert "external_id" in match_columns

    processed_pk = inspector.get_pk_constraint("processed_events")["constrained_columns"]
    assert processed_pk == ["event_id"]


def test_user_has_one_prediction_per_match() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        match = Match(
            external_id="match-1",
            sport="football",
            home_id="home",
            home_name="Home",
            away_id="away",
            away_name="Away",
            starts_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
            status=MatchStatus.scheduled,
        )
        session.add(match)
        session.commit()

        session.add(
            UserPrediction(
                user_id="user-1",
                match_id=match.id,
                pick=Outcome.home,
                status=PredictionStatus.open,
            )
        )
        session.commit()

        session.add(
            UserPrediction(
                user_id="user-1",
                match_id=match.id,
                pick=Outcome.away,
                status=PredictionStatus.open,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
