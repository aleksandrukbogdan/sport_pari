from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    news_id: int
    author_id: str
    body: str
    created_at: datetime
