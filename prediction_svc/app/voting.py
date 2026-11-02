from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events import EventType, SportsEvent
from app.models import Match, Question, QuestionKind, QuestionStatus, VoteCast, VoteChoice


class UnknownMatch(Exception):
    pass


def yes_share(yes: int, no: int) -> float | None:
    total = yes + no
    if total == 0:
        return None
    return round(yes / total, 4)


def match_copy(session: Session, external_id: str | None) -> Match | None:
    if external_id is None:
        return None
    return session.scalar(select(Match).where(Match.external_id == external_id))


def create_question(
    session: Session,
    title: str,
    kind: QuestionKind,
    match_external_id: str | None,
) -> Question:
    if kind is QuestionKind.match and match_copy(session, match_external_id) is None:
        raise UnknownMatch(match_external_id)
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
        session.scalars(select(VoteCast).where(VoteCast.question_id == question_id).order_by(VoteCast.id)).all()
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


def close_question(session: Session, question_id) -> str:
    question = session.get(Question, question_id)
    if question is None:
        return "missing"
    if question.status != QuestionStatus.open:
        return "closed"
    question.status = QuestionStatus.closed
    session.commit()
    return "closed"


def apply_match_facts(session: Session, event: SportsEvent) -> None:
    if event.event_type not in {EventType.finished, EventType.cancelled, EventType.result_corrected}:
        return
    questions = session.scalars(
        select(Question).where(
            Question.kind == QuestionKind.match,
            Question.match_external_id == event.match.id,
        )
    ).all()
    for question in questions:
        if event.event_type == EventType.cancelled:
            question.status = QuestionStatus.withdrawn
            question.factual_outcome = None
            continue
        if question.status == QuestionStatus.withdrawn:
            continue
        question.status = QuestionStatus.closed
        question.factual_outcome = event.match.outcome


def cast_vote(session: Session, question_id, user_id: str, choice: VoteChoice) -> str:
    question = session.get(Question, question_id)
    if question is None:
        return "missing"
    if question.status != QuestionStatus.open:
        return "closed"

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
