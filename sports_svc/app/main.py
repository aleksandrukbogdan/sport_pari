from fastapi import FastAPI, HTTPException, Query
from psycopg.errors import UniqueViolation

from app import database
from app.schemas import Match, Score
from app.statistics import team_statistics, standings
from app.events import create_event

app = FastAPI(title="Sports Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/matches", response_model=list[Match])
def list_matches(season_id: int | None = Query(default=None, gt=0)):
    matches = database.read_matches()

    if season_id is None:
        return matches

    result = []
    for match in matches:
        if match.season_id == season_id:
            result.append(match)

    return result


@app.get("/matches/{match_id}", response_model=Match)
def get_match(match_id: int):
    match = database.read_match(match_id)

    if match is None:
        raise HTTPException(status_code=404, detail="Матч не найден")

    return match


@app.post("/matches", response_model=Match, status_code=201)
def add_match(new_match: Match):
    event = None

    if new_match.status == "scheduled":
        event = create_event(new_match, "match.scheduled")

    try:
        database.insert_match(new_match, event)
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Такой номер матча уже есть"
        )

    return new_match


@app.get("/teams/{team_id}/stats")
def get_team_statistics(team_id: int, season_id: int = Query(gt=0)):
    matches = database.read_matches()
    result = team_statistics(matches, team_id, season_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Команда не найдена в этом сезоне"
        )

    return result


@app.get("/standings")
def get_standings(season_id: int = Query(gt=0)):
    return standings(database.read_matches(), season_id)


def save_match_change(match: Match, changes: dict, event_type: str):
    # Проверяем новую версию матча перед сохранением.
    data = match.model_dump()
    data.update(changes)
    updated_match = Match.model_validate(data)
    event = create_event(updated_match, event_type)

    try:
        database.update_match(match, updated_match, event)
    except database.MatchChangedError as error:
        raise HTTPException(status_code=409, detail=str(error))

    return updated_match


@app.post("/matches/{match_id}/start", response_model=Match)
def start_match(match_id: int):
    match = get_match(match_id)

    if match.status != "scheduled":
        raise HTTPException(
            status_code=409,
            detail="Начать можно только запланированный матч"
        )

    return save_match_change(
        match,
        {"status": "live", "score": {"home": 0, "away": 0}},
        "match.started"
    )


@app.post("/matches/{match_id}/score", response_model=Match)
def update_score(match_id: int, score: Score):
    match = get_match(match_id)

    if match.status != "live":
        raise HTTPException(
            status_code=409,
            detail="Менять счёт можно только во время матча"
        )

    if match.score == score:
        return match

    return save_match_change(
        match,
        {"score": score.model_dump()},
        "match.score_changed"
    )


@app.post("/matches/{match_id}/finish", response_model=Match)
def finish_match(match_id: int, score: Score):
    match = get_match(match_id)

    if match.status != "live":
        raise HTTPException(
            status_code=409,
            detail="Завершить можно только начатый матч"
        )

    return save_match_change(
        match,
        {"status": "finished", "score": score.model_dump()},
        "match.finished"
    )


@app.post("/matches/{match_id}/cancel", response_model=Match)
def cancel_match(match_id: int):
    match = get_match(match_id)

    if match.status not in ["scheduled", "live"]:
        raise HTTPException(
            status_code=409,
            detail="Этот матч уже завершён или отменён"
        )

    return save_match_change(
        match,
        {"status": "cancelled"},
        "match.cancelled"
    )


@app.post("/matches/{match_id}/correct-result", response_model=Match)
def correct_result(match_id: int, score: Score):
    match = get_match(match_id)

    if match.status != "finished":
        raise HTTPException(
            status_code=409,
            detail="Исправить можно только завершённый матч"
        )

    if match.score == score:
        raise HTTPException(status_code=409, detail="Счёт не изменился")

    return save_match_change(
        match,
        {"score": score.model_dump()},
        "match.result_corrected"
    )


@app.get("/events")
def list_events():
    #Читаем события из базы. Отправки в Kafka пока нет
    return database.read_events()