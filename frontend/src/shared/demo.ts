import type { HeadToHead, MatchItem, NewsCard, NewsDetail, QuestionItem, Standing } from "@/shared/types";

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

// Эти две встречи видны и в списке матчей, и в истории пары Б — В.
const demoMeetings: MatchItem[] = [
  {
    match_id: 201, sport: "football", season_id: 1,
    home: { id: 3, name: "Команда В" }, away: { id: 2, name: "Команда Б" },
    starts_at: "2026-11-12T15:00:00Z", status: "finished", score: { home: 1, away: 2 },
  },
  {
    match_id: 202, sport: "football", season_id: 1,
    home: { id: 2, name: "Команда Б" }, away: { id: 3, name: "Команда В" },
    starts_at: "2026-10-04T15:00:00Z", status: "finished", score: { home: 0, away: 0 },
  },
];

demoMatches.push(...demoMeetings);

export const demoHeadToHeads: Record<string, HeadToHead> = {
  "3": { matches: demoMeetings, summary: { home_wins: 1, draws: 1, away_wins: 0 } },
  "201": {
    matches: demoMeetings.slice(1), summary: { home_wins: 0, draws: 1, away_wins: 0 },
  },
};

export const demoStandings: Standing[] = [
  {
    position: 1, team_id: 2, team_name: "Команда Б", season_id: 1,
    played: 3, wins: 1, draws: 1, losses: 1, goals_for: 3, goals_against: 3,
    goal_difference: 0, points: 4, recent_form: ["win", "draw", "loss"],
  },
  {
    position: 2, team_id: 1, team_name: "Команда А", season_id: 1,
    played: 1, wins: 1, draws: 0, losses: 0, goals_for: 2, goals_against: 1,
    goal_difference: 1, points: 3, recent_form: ["win"],
  },
  {
    position: 3, team_id: 3, team_name: "Команда В", season_id: 1,
    played: 2, wins: 0, draws: 1, losses: 1, goals_for: 1, goals_against: 2,
    goal_difference: -1, points: 1, recent_form: ["loss", "draw"],
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
