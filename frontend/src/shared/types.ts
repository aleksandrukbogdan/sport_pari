export type NewsCard = {
  id: number;
  title: string;
  summary: string;
  sport_id: string;
  published_at: string;
  comments_count: number;
  source_name?: string | null;
  source_url?: string | null;
  image_url?: string | null;
};

export type NewsDetail = NewsCard & { body: string };

export type CommentItem = {
  id: number;
  news_id: number;
  author_id: string;
  body: string;
  created_at: string;
};

export type Recommendation = {
  news_id: number;
  score: number;
  reason: string;
};

export type Team = { id: number; name: string };
export type MatchItem = {
  match_id: number;
  sport: string;
  season_id: number;
  home: Team;
  away: Team;
  starts_at: string;
  status: "scheduled" | "live" | "finished" | "cancelled";
  score: { home: number; away: number } | null;
};

export type HeadToHead = {
  matches: MatchItem[];
  summary: { home_wins: number; draws: number; away_wins: number };
};

export type Standing = {
  position?: number;
  team_id: number;
  team_name: string;
  season_id?: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  recent_form?: ("win" | "draw" | "loss")[];
};

export type QuestionItem = {
  id: string;
  title: string;
  kind: "match" | "event";
  match_external_id: string | null;
  home_name: string | null;
  away_name: string | null;
  starts_at: string | null;
  match_status: string | null;
  status: "open" | "closed" | "withdrawn";
  factual_outcome: "home" | "draw" | "away" | null;
  yes: number;
  no: number;
  yes_share: number | null;
  my_choice: "yes" | "no" | null;
};

export type Viewer = { username: string; isAdmin: boolean; demo: boolean };

export type LoadResult<T> = { ok: true; data: T; demo: boolean } | { ok: false; message: string; demo: boolean };
