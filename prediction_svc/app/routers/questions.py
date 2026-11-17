import uuid
from datetime import datetime
from typing import Self

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.auth import TokenIdentity
from app.auth import identity_from_bearer
from app.auth import is_admin
from app.config import get_settings
from app.db import get_db
from app.models import Question, QuestionKind, VoteChoice
from app.models import QuestionStatus
from app.voting import (
    UnknownMatch,
    cast_vote,
    casts_for,
    chart,
    close_question,
    create_question,
    latest_choice,
    list_questions,
    match_copy,
    yes_share,
)

router = APIRouter(prefix="/questions", tags=["questions"])
_bearer = HTTPBearer(auto_error=False)


class QuestionBody(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    kind: QuestionKind
    match_external_id: str | None = None

    @model_validator(mode="after")
    def match_question_names_a_match(self) -> Self:
        if self.kind is QuestionKind.match and not self.match_external_id:
            raise ValueError("match question needs match_external_id")
        if self.kind is QuestionKind.event:
            self.match_external_id = None
        return self


class VoteBody(BaseModel):
    choice: VoteChoice


class QuestionView(BaseModel):
    id: uuid.UUID
    title: str
    kind: QuestionKind
    match_external_id: str | None
    home_name: str | None = None
    away_name: str | None = None
    starts_at: datetime | None = None
    match_status: str | None = None
    status: QuestionStatus
    factual_outcome: str | None = None
    yes: int
    no: int
    yes_share: float | None
    my_choice: VoteChoice | None = None


class ChartPoint(BaseModel):
    at: object
    yes: int
    no: int
    yes_share: float | None


class ChartView(BaseModel):
    question_id: uuid.UUID
    yes: int
    no: int
    yes_share: float | None
    points: list[ChartPoint]


class MeView(BaseModel):
    sub: str
    preferred_username: str | None
    is_admin: bool


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str | None:
    if credentials is None:
        return None
    return require_identity(credentials).sub


def require_identity(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> TokenIdentity:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return identity_from_bearer(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_user(identity: TokenIdentity = Depends(require_identity)) -> str:
    return identity.sub


def require_admin(identity: TokenIdentity = Depends(require_identity)) -> str:
    if not is_admin(identity, get_settings().admin_user_ids):
        raise HTTPException(status_code=403, detail="admin only")
    return identity.sub


def view_question(session: Session, question: Question, user_id: str | None = None) -> QuestionView:
    yes, no, _points = chart(casts_for(session, question.id))
    match = match_copy(session, question.match_external_id)
    return QuestionView(
        id=question.id,
        title=question.title,
        kind=question.kind,
        match_external_id=question.match_external_id,
        home_name=None if match is None else match.home_name,
        away_name=None if match is None else match.away_name,
        starts_at=None if match is None else match.starts_at,
        match_status=None if match is None else match.status.value,
        status=question.status,
        factual_outcome=None if question.factual_outcome is None else question.factual_outcome.value,
        yes=yes,
        no=no,
        yes_share=yes_share(yes, no),
        my_choice=None if user_id is None else latest_choice(session, question.id, user_id),
    )


@router.post("", response_model=QuestionView, status_code=201)
def post_question(
    body: QuestionBody,
    _: str = Depends(require_admin),
    session: Session = Depends(get_db),
) -> QuestionView:
    try:
        question = create_question(session, body.title, body.kind, body.match_external_id)
    except UnknownMatch:
        raise HTTPException(status_code=404, detail="match not found") from None
    return view_question(session, question)


@router.get("", response_model=list[QuestionView])
def get_questions(
    kind: QuestionKind | None = None,
    user_id: str | None = Depends(optional_user),
    session: Session = Depends(get_db),
) -> list[QuestionView]:
    return [view_question(session, question, user_id) for question in list_questions(session, kind)]


@router.get("/{question_id}", response_model=QuestionView)
def get_question(
    question_id: uuid.UUID,
    user_id: str | None = Depends(optional_user),
    session: Session = Depends(get_db),
) -> QuestionView:
    question = session.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")
    return view_question(session, question, user_id)


@router.post("/{question_id}/close", response_model=QuestionView)
def post_close(
    question_id: uuid.UUID,
    _: str = Depends(require_admin),
    session: Session = Depends(get_db),
) -> QuestionView:
    result = close_question(session, question_id)
    if result == "missing":
        raise HTTPException(status_code=404, detail="question not found")
    question = session.get(Question, question_id)
    return view_question(session, question)


@router.post("/{question_id}/votes", response_model=QuestionView)
def post_vote(
    question_id: uuid.UUID,
    body: VoteBody,
    user_id: str = Depends(require_user),
    session: Session = Depends(get_db),
) -> QuestionView:
    result = cast_vote(session, question_id, user_id, body.choice)
    if result == "missing":
        raise HTTPException(status_code=404, detail="question not found")
    if result == "closed":
        raise HTTPException(status_code=409, detail="voting is closed")
    question = session.get(Question, question_id)
    return view_question(session, question, user_id)


@router.get("/{question_id}/chart", response_model=ChartView)
def get_chart(question_id: uuid.UUID, session: Session = Depends(get_db)) -> ChartView:
    question = session.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")
    yes, no, points = chart(casts_for(session, question.id))
    return ChartView(
        question_id=question.id,
        yes=yes,
        no=no,
        yes_share=yes_share(yes, no),
        points=points,
    )
