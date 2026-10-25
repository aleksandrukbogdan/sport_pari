from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question, QuestionKind, VoteCast, VoteChoice


def yes_share(yes: int, no: int) -> float | None:
    total = yes + no
    if total == 0:
        return None
    return round(yes / total, 4)


def create_question(
    session: Session,
    title: str,
    kind: QuestionKind,
    match_external_id: str | None,
) -> Question:
    question = Question(title=title, kind=kind, match_external_id=match_external_id)
    session.add(question)
    session.commit()
    return question


def list_questions(session: Session, kind: QuestionKind | None) -> list[Question]:
    query = select(Question).order_by(Question.created_at, Question.id)
    if kind is not None:
        query = query.where(Question.kind == kind)
    return list(session.scalars(query).all())


def casts_for(session: Session, question_id) -> list[VoteCast]:
    return list(
        session.scalars(
            select(VoteCast).where(VoteCast.question_id == question_id).order_by(VoteCast.id)
        ).all()
    )


def chart(casts: list[VoteCast]) -> tuple[int, int, list[dict]]:
    latest: dict[str, VoteChoice] = {}
    points: list[dict] = []
    for cast in casts:
        latest[cast.user_id] = cast.choice
        yes = sum(choice == VoteChoice.yes for choice in latest.values())
        no = len(latest) - yes
        points.append(
            {
                "at": cast.created_at,
                "yes": yes,
                "no": no,
                "yes_share": yes_share(yes, no),
            }
        )
    if not points:
        return 0, 0, []
    return points[-1]["yes"], points[-1]["no"], points


def cast_vote(session: Session, question_id, user_id: str, choice: VoteChoice) -> str:
    question = session.get(Question, question_id)
    if question is None:
        return "missing"

    previous = session.scalar(
        select(VoteCast)
        .where(VoteCast.question_id == question_id, VoteCast.user_id == user_id)
        .order_by(VoteCast.id.desc())
    )
    if previous is not None and previous.choice == choice:
        return "unchanged"

    session.add(
        VoteCast(
            question_id=question_id,
            user_id=user_id,
            choice=choice,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    return "cast"
