from app.schemas import Match


def team_statistics(matches: list[Match], team_id: int, season_id: int):
    # поиск команды среди матчей выбранного сезона
    team = None
    for match in matches:
        if match.season_id != season_id:
            continue
        if match.home.id == team_id:
            team = match.home
        elif match.away.id == team_id:
            team = match.away

    if team is None:
        return None

    result = {
        "team_id": team.id,
        "team_name": team.name,
        "season_id": season_id,
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_difference": 0,
        "points": 0,
    }

    recent_results = []
    for match in matches:
        # Учитываем только завершённые матчи нужного сезона.
        if match.season_id != season_id or match.status != "finished":
            continue

        # для гостей забитые и пропущенные голы меняются местами
        if match.home.id == team_id:
            scored = match.score.home
            conceded = match.score.away
        elif match.away.id == team_id:
            scored = match.score.away
            conceded = match.score.home
        else:
            continue

        result["played"] += 1
        result["goals_for"] += scored
        result["goals_against"] += conceded

        if scored > conceded:
            result["wins"] += 1
            outcome = "win"
        elif scored == conceded:
            result["draws"] += 1
            outcome = "draw"
        else:
            result["losses"] += 1
            outcome = "loss"
        recent_results.append((match.starts_at, match.match_id, outcome))

    result["goal_difference"] = result["goals_for"] - result["goals_against"]
    result["points"] = result["wins"] * 3 + result["draws"]
    # При одинаковом времени используем номер матча для стабильного порядка.
    recent_results.sort(reverse=True)
    result["recent_form"] = [outcome for _, _, outcome in recent_results[:5]]
    return result


def standings(matches: list[Match], season_id: int):
    # собираются номера команд без повторений
    team_ids = set()
    for match in matches:
        if match.season_id == season_id:
            team_ids.add(match.home.id)
            team_ids.add(match.away.id)

    table = []
    for team_id in team_ids:
        table.append(team_statistics(matches, team_id, season_id))

    # больше очков, разница голов и забитые голы — выше место. При полном равенстве используем номер команды для стабильного порядка.
    table.sort(key=table_order)
    for position, row in enumerate(table, start=1):
        row["position"] = position
    return table


def table_order(row):
    return (-row["points"], -row["goal_difference"], -row["goals_for"], row["team_id"])


def head_to_head(matches: list[Match], current: Match, limit: int = 5):
    home_id = current.home.id
    team_ids = {home_id, current.away.id}
    meetings = [
        match for match in matches
        if match.match_id != current.match_id
        and match.starts_at < current.starts_at
        and match.status == "finished"
        and match.sport == current.sport
        and {match.home.id, match.away.id} == team_ids
    ]
    meetings.sort(key=lambda match: (match.starts_at, match.match_id), reverse=True)
    meetings = meetings[:limit]

    summary = {"home_wins": 0, "draws": 0, "away_wins": 0}
    for match in meetings:
        # Считаем победы с позиции команд текущего матча.
        home_score, away_score = match.score.home, match.score.away
        if match.home.id != home_id:
            home_score, away_score = away_score, home_score
        if home_score == away_score:
            summary["draws"] += 1
        elif home_score > away_score:
            summary["home_wins"] += 1
        else:
            summary["away_wins"] += 1

    return {"matches": meetings, "summary": summary}
