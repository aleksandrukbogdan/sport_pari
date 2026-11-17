import { cookies } from "next/headers";

import { demoArticle, demoHeadToHeads, demoMatches, demoNews, demoQuestions, demoStandings } from "@/shared/demo";
import { errorMessage, isDemo } from "@/shared/labels";
import type { CommentItem, HeadToHead, LoadResult, MatchItem, NewsCard, NewsDetail, QuestionItem, Recommendation, Standing, Viewer } from "@/shared/types";

type ServiceName = "user" | "news" | "sports" | "prediction";

function baseUrl(service: ServiceName) {
  const values = {
    user: process.env.USER_API_URL ?? "http://localhost:8001",
    news: process.env.NEWS_API_URL ?? "http://localhost:8002",
    sports: process.env.SPORTS_API_URL ?? "http://localhost:8003",
    prediction: process.env.PREDICTION_API_URL ?? "http://localhost:8004",
  };
  return values[service].replace(/\/$/, "");
}

export function subjectFromToken(token: string) {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const payload = JSON.parse(Buffer.from(part, "base64url").toString("utf8")) as { sub?: unknown };
    return typeof payload.sub === "string" && payload.sub ? payload.sub : null;
  } catch {
    return null;
  }
}

async function accessToken() {
  const jar = await cookies();
  return jar.get("access_token")?.value;
}

function detailFrom(payload: unknown) {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return "";
  const detail = (payload as { detail: unknown }).detail;
  return typeof detail === "string" ? detail : "";
}

export async function apiGet<T>(service: ServiceName, path: string, options?: { auth?: boolean; userHeader?: boolean }): Promise<LoadResult<T>> {
  if (isDemo()) return { ok: false, message: "Демонстрационный режим", demo: true };
  const headers = new Headers();
  const token = await accessToken();
  if (options?.auth && token) headers.set("authorization", `Bearer ${token}`);
  if (options?.userHeader && token) {
    const subject = subjectFromToken(token);
    if (subject) headers.set("x-user-id", subject);
  }
  try {
    const response = await fetch(`${baseUrl(service)}${path}`, { headers, cache: "no-store" });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      return { ok: false, demo: false, message: errorMessage(response.status, detailFrom(payload), "Не удалось загрузить данные. Попробуйте ещё раз.") };
    }
    return { ok: true, demo: false, data: payload as T };
  } catch {
    return { ok: false, demo: false, message: "Не удалось связаться с сервисом. Попробуйте ещё раз." };
  }
}

export async function loadViewer(): Promise<Viewer | null> {
  const jar = await cookies();
  if (isDemo()) {
    if (jar.get("demo_session")?.value !== "1") return null;
    return { username: "student", isAdmin: true, demo: true };
  }
  const token = jar.get("access_token")?.value;
  if (!token) return null;
  const profile = await apiGet<{ username: string }>("user", "/user", { auth: true });
  if (!profile.ok) return null;
  const me = await apiGet<{ is_admin: boolean }>("prediction", "/me", { auth: true });
  return { username: profile.data.username, isAdmin: me.ok ? me.data.is_admin : false, demo: false };
}

export async function loadNews(sportId?: string): Promise<LoadResult<NewsCard[]>> {
  if (isDemo()) return { ok: true, demo: true, data: demoNews.filter((item) => !sportId || item.sport_id === sportId) };
  const query = sportId ? `?sport_id=${encodeURIComponent(sportId)}` : "";
  return apiGet<NewsCard[]>("news", `/api/v1/news${query}`);
}

export async function loadArticle(id: string): Promise<LoadResult<NewsDetail>> {
  if (isDemo()) {
    if (id !== "1") return { ok: false, demo: true, message: "Материал не найден." };
    return { ok: true, demo: true, data: demoArticle };
  }
  return apiGet<NewsDetail>("news", `/api/v1/news/${encodeURIComponent(id)}`);
}

export async function loadComments(id: string): Promise<LoadResult<CommentItem[]>> {
  if (isDemo()) {
    return {
      ok: true,
      demo: true,
      data: [{ id: 1, news_id: 1, author_id: "student", body: "Демонстрационный комментарий.", created_at: "2026-11-15T12:00:00Z" }],
    };
  }
  return apiGet<CommentItem[]>("news", `/api/v1/news/${encodeURIComponent(id)}/comments`);
}

export async function loadRecommendations(): Promise<LoadResult<Recommendation[]>> {
  if (isDemo()) return { ok: true, demo: true, data: [{ news_id: 1, score: 1, reason: "sport" }] };
  return apiGet<Recommendation[]>("news", "/api/v1/recommendations", { userHeader: true });
}

export async function loadMatches(seasonId?: string): Promise<LoadResult<MatchItem[]>> {
  if (isDemo()) {
    const season = seasonId ? Number(seasonId) : null;
    return { ok: true, demo: true, data: demoMatches.filter((item) => season === null || item.season_id === season) };
  }
  const query = seasonId ? `?season_id=${encodeURIComponent(seasonId)}` : "";
  return apiGet<MatchItem[]>("sports", `/matches${query}`);
}

export async function loadMatch(id: string): Promise<LoadResult<MatchItem>> {
  if (isDemo()) {
    const match = demoMatches.find((item) => String(item.match_id) === id);
    if (!match) return { ok: false, demo: true, message: "Матч не найден." };
    return { ok: true, demo: true, data: match };
  }
  return apiGet<MatchItem>("sports", `/matches/${encodeURIComponent(id)}`);
}

export async function loadHeadToHead(id: string): Promise<LoadResult<HeadToHead>> {
  if (isDemo()) {
    const data = demoHeadToHeads[id] ?? {
      matches: [], summary: { home_wins: 0, draws: 0, away_wins: 0 },
    };
    return { ok: true, demo: true, data };
  }
  return apiGet<HeadToHead>("sports", `/matches/${encodeURIComponent(id)}/head-to-head`);
}

export async function loadStandings(seasonId: string): Promise<LoadResult<Standing[]>> {
  if (isDemo()) return { ok: true, demo: true, data: demoStandings };
  return apiGet<Standing[]>("sports", `/standings?season_id=${encodeURIComponent(seasonId)}`);
}

export async function loadTeamStats(teamId: string, seasonId: string): Promise<LoadResult<Standing>> {
  if (isDemo()) {
    const row = demoStandings.find((item) => String(item.team_id) === teamId);
    if (!row) return { ok: false, demo: true, message: "Для этого показателя пока нет данных." };
    return { ok: true, demo: true, data: row };
  }
  return apiGet<Standing>("sports", `/teams/${encodeURIComponent(teamId)}/stats?season_id=${encodeURIComponent(seasonId)}`);
}

export async function loadQuestions(kind?: string, auth = false): Promise<LoadResult<QuestionItem[]>> {
  if (isDemo()) return { ok: true, demo: true, data: demoQuestions.filter((item) => !kind || item.kind === kind) };
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiGet<QuestionItem[]>("prediction", `/questions${query}`, { auth });
}

export async function loadQuestion(id: string): Promise<LoadResult<QuestionItem>> {
  if (isDemo()) {
    const question = demoQuestions.find((item) => item.id === id);
    if (!question) return { ok: false, demo: true, message: "Вопрос не найден." };
    return { ok: true, demo: true, data: question };
  }
  return apiGet<QuestionItem>("prediction", `/questions/${encodeURIComponent(id)}`, { auth: true });
}
