from typing import Literal

from pydantic import BaseModel, Field


class ViewCreate(BaseModel):
    news_id: int = Field(ge=1)


class Recommendation(BaseModel):
    news_id: int
    score: float
    reason: Literal["popularity", "content", "sport", "blend"]
