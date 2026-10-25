import uuid
from typing import Self

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Question, QuestionKind, VoteChoice
from app.voting import cast_vote, casts_for, chart, create_question, list_questions, yes_share

router = APIRouter(prefix="/questions", tags=["questions"])


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
    yes: int
    no: int
    yes_share: float | None


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


def require_user(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing user")
    return x_user_id


def require_admin(user_id: str = Depends(require_user)) -> str:
    admins = {item.strip() for item in get_settings().admin_user_ids.split(",") if item.strip()}
    if user_id not in admins:
        raise HTTPException(status_code=403, detail="admin only")
    return user_id


def view_question(session: Session, question: Question) -> QuestionView:
    yes, no, _points = chart(casts_for(session, question.id))
    return QuestionView(
        id=question.id,
        title=question.title,
        kind=question.kind,
        match_external_id=question.match_external_id,
        yes=yes,
        no=no,
        yes_share=yes_share(yes, no),
    )


@router.post("", response_model=QuestionView, status_code=201)
def post_question(
    body: QuestionBody,
    _: str = Depends(require_admin),
    session: Session = Depends(get_db),
) -> QuestionView:
    question = create_question(session, body.title, body.kind, body.match_external_id)
    return view_question(session, question)


@router.get("", response_model=list[QuestionView])
def get_questions(
    kind: QuestionKind | None = None,
    session: Session = Depends(get_db),
) -> list[QuestionView]:
    return [view_question(session, question) for question in list_questions(session, kind)]


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
    question = session.get(Question, question_id)
    return view_question(session, question)


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
