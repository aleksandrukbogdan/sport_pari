from app.schemas import Match, Score, Team


TEAM_A = Team(id=1, name="Команда А")
TEAM_B = Team(id=2, name="Команда Б")
TEAM_C = Team(id=3, name="Команда В")

#пусть 2 матча закончились, а третий ещё не начался.
MATCHES = [
    Match(match_id=1, season_id=1, home=TEAM_A, away=TEAM_B,
          starts_at="2026-10-01T15:00:00Z", status="finished",
          score=Score(home=2, away=1)),
    Match(match_id=2, season_id=1, home=TEAM_C, away=TEAM_A,
          starts_at="2026-10-02T15:00:00Z", status="finished",
          score=Score(home=0, away=0)),
    Match(match_id=3, season_id=1, home=TEAM_B, away=TEAM_C,
          starts_at="2026-11-01T15:00:00Z", status="scheduled"),
]
