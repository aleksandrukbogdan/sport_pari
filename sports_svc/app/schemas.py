from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


#данные одной команды. BaseModel проверяет, подходят ли значения к указанным типам
class Team(BaseModel):
    id: int = Field(gt=0)  #номер команды больше нуля
    name: str = Field(min_length=1)  


#счёт хозяев и гостей
class Score(BaseModel):
    home: int = Field(ge=0)
    away: int = Field(ge=0)


#данные матча
class Match(BaseModel):
    match_id: int = Field(gt=0)
    sport: Literal["football"] = "football"  
    season_id: int = Field(gt=0)
    home: Team  # Хозяева.
    away: Team  # Гости.
    starts_at: datetime  #время начала матча
    #Literal разрешает только перечисленные значения, которые мы указываем
    status: Literal["scheduled", "live", "finished", "cancelled"]
    score: Score | None = None  #счета еще нет

    #проверка после проверки типов полей
    @model_validator(mode="after")
    def check_match(self):
        if self.home.id == self.away.id:
            raise ValueError("Команда не может играть сама с собой")

        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("Укажите часовой пояс")

        if self.status == "finished" and self.score is None:
            raise ValueError("У завершённого матча должен быть счёт")

        if self.status == "scheduled" and self.score is not None:
            raise ValueError("У запланированного матча ещё нет счёта")

        return self
