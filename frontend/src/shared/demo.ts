import type { MatchItem, NewsCard, NewsDetail, QuestionItem, Standing } from "@/shared/types";

const now = "2026-11-15T12:00:00Z";

export const demoNews: NewsCard[] = [
  {
    id: 1,
    title: "Учебный пример: форвард пропустит ближайший матч",
    summary: "Демонстрационная заметка для разбора состава. Это не реальная травма.",
    sport_id: "football",
    published_at: now,
    comments_count: 1,
  },
];

export const demoArticle: NewsDetail = {
  ...demoNews[0],
  body: "Демонстрационные данные. Материал нужен, чтобы открыть страницу статьи без новостного сервиса.",
};

export const demoMatches: MatchItem[] = [
  {
    match_id: 3,
    sport: "football",
    season_id: 1,
    home: { id: 2, name: "Команда Б" },
    away: { id: 3, name: "Команда В" },
    starts_at: "2026-11-20T15:00:00Z",
    status: "scheduled",
    score: null,
  },
  {
    match_id: 1,
    sport: "football",
    season_id: 1,
    home: { id: 1, name: "Команда А" },
    away: { id: 2, name: "Команда Б" },
    starts_at: "2026-10-01T15:00:00Z",
    status: "finished",
    score: { home: 2, away: 1 },
  },
];

export const demoStandings: Standing[] = [
  {
    position: 1,
    team_id: 1,
    team_name: "Команда А",
    played: 2,
    wins: 1,
    draws: 1,
    losses: 0,
    goals_for: 2,
    goals_against: 1,
    goal_difference: 1,
    points: 4,
  },
];

export const demoQuestions: QuestionItem[] = [
  {
    id: "demo-question",
    title: "Команда Б победит в основное время?",
    kind: "match",
    match_external_id: "3",
    home_name: "Команда Б",
    away_name: "Команда В",
    starts_at: "2026-11-20T15:00:00Z",
    match_status: "scheduled",
    status: "open",
    factual_outcome: null,
    yes: 0,
    no: 0,
    yes_share: null,
    my_choice: null,
  },
];
