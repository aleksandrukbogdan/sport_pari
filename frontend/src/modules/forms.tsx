"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { errorMessage } from "@/shared/labels";
import type { MatchItem, QuestionItem } from "@/shared/types";

async function readDetail(response: Response) {
  const payload = await response.json().catch(() => null);
  const detail = payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string" ? payload.detail : "";
  return { detail, payload };
}

export function AuthForm({ mode, nextPath, demo }: { mode: "login" | "register"; nextPath: string; demo: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body = mode === "login"
      ? { username: String(form.get("username") ?? ""), password: String(form.get("password") ?? "") }
      : { username: String(form.get("username") ?? ""), email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") };
    const response = await fetch(mode === "login" ? "/api/auth/login" : "/api/auth/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const { detail } = await readDetail(response);
    setPending(false);
    if (!response.ok) {
      setError(errorMessage(response.status, detail, mode === "login" ? "Не удалось войти." : "Не удалось зарегистрироваться."));
      return;
    }
    if (mode === "register") {
      setDone(demo ? "Демонстрационный режим: учётная запись не создана." : "Учётная запись создана. Теперь можно войти.");
      return;
    }
    router.push(nextPath || "/");
    router.refresh();
  }

  return (
    <form className="stack surface" onSubmit={onSubmit}>
      {demo ? <p>Демонстрационные данные. Сервер пользователей не вызывается.</p> : null}
      <label className="field">
        <span>Имя пользователя</span>
        <input name="username" autoComplete="username" required />
      </label>
      {mode === "register" ? (
        <label className="field">
          <span>Электронная почта</span>
          <input name="email" type="email" autoComplete="email" required />
        </label>
      ) : null}
      <label className="field">
        <span>Пароль</span>
        <input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required />
      </label>
      {error ? <p role="alert">{error}</p> : null}
      {done ? <p role="status">{done}</p> : null}
      <button className="button primary" type="submit" disabled={pending}>
        {pending ? "Отправляем…" : mode === "login" ? (demo ? "Войти в демонстрацию" : "Войти") : "Зарегистрироваться"}
      </button>
    </form>
  );
}

export function CommentForm({ newsId, demo }: { newsId: number; demo: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (demo) {
      setError("Демонстрационный комментарий не отправляется на сервер.");
      return;
    }
    setPending(true);
    setError("");
    const response = await fetch(`/api/gateway/news/api/v1/news/${newsId}/comments`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ body: text }),
    });
    const { detail } = await readDetail(response);
    setPending(false);
    if (!response.ok) {
      setError(errorMessage(response.status, detail, "Не удалось отправить комментарий."));
      return;
    }
    setText("");
    router.refresh();
  }

  return (
    <form className="stack" onSubmit={onSubmit}>
      <label className="field">
        <span>Комментарий</span>
        <textarea name="body" value={text} onChange={(event) => setText(event.target.value)} required />
      </label>
      {error ? <p role="alert">{error}</p> : null}
      <button className="button primary" type="submit" disabled={pending}>{pending ? "Отправляем…" : "Отправить"}</button>
    </form>
  );
}

export function VoteForm({ question, demo }: { question: QuestionItem; demo: boolean }) {
  const router = useRouter();
  const [choice, setChoice] = useState(question.my_choice ?? "yes");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const closed = question.status !== "open";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (demo) {
      setMessage("Демонстрационный ответ, сервер не вызывался.");
      return;
    }
    setPending(true);
    const response = await fetch(`/api/gateway/prediction/questions/${question.id}/votes`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ choice }),
    });
    const { detail } = await readDetail(response);
    setPending(false);
    if (!response.ok) {
      setError(errorMessage(response.status, detail, "Не удалось отправить прогноз."));
      return;
    }
    setMessage("Ваш прогноз принят.");
    router.refresh();
  }

  return (
    <form className="stack" onSubmit={onSubmit}>
      <fieldset className="stack" disabled={closed || pending}>
        <legend className="muted">Ответ</legend>
        <label className="check"><input type="radio" name="choice" checked={choice === "yes"} onChange={() => setChoice("yes")} /><span>Да</span></label>
        <label className="check"><input type="radio" name="choice" checked={choice === "no"} onChange={() => setChoice("no")} /><span>Нет</span></label>
      </fieldset>
      {closed ? <p>Голосование закрыто.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {message ? <p role="status">{message}</p> : null}
      <button className="button primary" type="submit" disabled={closed || pending} title={closed ? "Голосование закрыто" : undefined}>
        {pending ? "Отправляем…" : "Отправить прогноз"}
      </button>
    </form>
  );
}

export function QuestionForm({ matches, demo }: { matches: MatchItem[]; demo: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [kind, setKind] = useState("match");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {
      title: String(form.get("title") ?? ""),
      kind,
      match_external_id: kind === "match" ? String(form.get("match_external_id") ?? "") : null,
    };
    if (demo) {
      setError("Демонстрационный вопрос не сохраняется на сервере.");
      return;
    }
    setPending(true);
    setError("");
    const response = await fetch("/api/gateway/prediction/questions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const { detail, payload } = await readDetail(response);
    setPending(false);
    if (!response.ok) {
      setError(errorMessage(response.status, detail, "Не удалось создать вопрос."));
      return;
    }
    const id = payload && typeof payload === "object" && "id" in payload ? String(payload.id) : "";
    router.push(id ? `/predictions/${id}` : "/predictions");
    router.refresh();
  }

  return (
    <form className="stack surface" onSubmit={onSubmit}>
      <label className="field">
        <span>Вопрос</span>
        <input name="title" required maxLength={300} placeholder="Команда Б победит в основное время?" />
      </label>
      <label className="field">
        <span>Тип</span>
        <select name="kind" value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="match">Матч</option>
          <option value="event">Событие</option>
        </select>
      </label>
      {kind === "match" ? (
        <label className="field">
          <span>Матч</span>
          <select name="match_external_id" required>
            {matches.map((match) => (
              <option key={match.match_id} value={match.match_id}>{match.home.name} — {match.away.name}</option>
            ))}
          </select>
        </label>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
      <button className="button primary" type="submit" disabled={pending}>{pending ? "Сохраняем…" : "Создать вопрос"}</button>
    </form>
  );
}

export function ProfileForms({ profile, interests, sessions, current }: {
  profile: { username: string; email: string };
  interests: { sport_ids: string[]; team_ids: string[] };
  sessions: { id: string; started_at: string; last_access_at: string; ip_address: string | null; is_current: boolean }[];
  current: boolean;
}) {
  const router = useRouter();
  const [sectionError, setSectionError] = useState("");
  const [status, setStatus] = useState("");
  const [pending, setPending] = useState(false);
  const [closing, setClosing] = useState<string | null>(null);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!current) return;
    const form = new FormData(event.currentTarget);
    await send("/api/gateway/user/user", "PATCH", {
      username: String(form.get("username") ?? ""),
      email: String(form.get("email") ?? ""),
    }, "Профиль сохранён.");
  }

  async function saveInterests(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!current) return;
    const form = new FormData(event.currentTarget);
    const split = (name: string) => String(form.get(name) ?? "").split(",").map((item) => item.trim()).filter(Boolean);
    await send("/api/gateway/user/user/interests", "PUT", { sport_ids: split("sport_ids"), team_ids: split("team_ids") }, "Интересы сохранены.");
  }

  async function send(url: string, method: string, body: unknown, success: string) {
    setPending(true);
    setSectionError("");
    setStatus("");
    const response = await fetch(url, { method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    const { detail } = await readDetail(response);
    setPending(false);
    if (!response.ok) {
      setSectionError(errorMessage(response.status, detail, "Не удалось сохранить."));
      return;
    }
    setStatus(success);
    router.refresh();
  }

  async function closeSession() {
    if (!closing || !current) return;
    setPending(true);
    const response = await fetch(`/api/gateway/user/user/sessions/${encodeURIComponent(closing)}`, { method: "DELETE" });
    const { detail } = await readDetail(response);
    setPending(false);
    setClosing(null);
    if (!response.ok) {
      setSectionError(errorMessage(response.status, detail, "Не удалось завершить сессию."));
      return;
    }
    setStatus("Сессия завершена.");
    router.refresh();
  }

  return (
    <div className="stack">
      {sectionError ? <p role="alert">{sectionError}</p> : null}
      {status ? <p role="status">{status}</p> : null}
      <form className="stack surface" onSubmit={saveProfile}>
        <h3 className="card-title">Профиль</h3>
        <label className="field"><span>Имя</span><input name="username" defaultValue={profile.username} required disabled={!current} /></label>
        <label className="field"><span>Почта</span><input name="email" type="email" defaultValue={profile.email} required disabled={!current} /></label>
        <button className="button primary" type="submit" disabled={!current || pending}>{pending ? "Сохраняем…" : "Сохранить"}</button>
        {!current ? <p className="muted">В демонстрации профиль не сохраняется на сервере.</p> : null}
      </form>
      <form className="stack surface" onSubmit={saveInterests}>
        <h3 className="card-title">Интересы</h3>
        <p className="muted">Интересы помогают подбирать новости. Каталог команд сервис не проверяет: укажите идентификаторы через запятую.</p>
        <label className="field"><span>Виды спорта</span><input name="sport_ids" defaultValue={interests.sport_ids.join(", ")} disabled={!current} /></label>
        <label className="field"><span>Команды</span><input name="team_ids" defaultValue={interests.team_ids.join(", ")} disabled={!current} /></label>
        <button className="button primary" type="submit" disabled={!current || pending}>Сохранить интересы</button>
      </form>
      <section className="surface stack">
        <h3 className="card-title">Сессии</h3>
        {sessions.length === 0 ? <p>Активных сессий нет.</p> : null}
        {sessions.map((session) => (
          <div className="row" key={session.id}>
            <span>{session.is_current ? "Текущая сессия" : "Другая сессия"}</span>
            <span className="muted">{session.ip_address ?? "Адрес неизвестен"}</span>
            {session.is_current ? null : (
              <button className="button danger" type="button" disabled={!current} onClick={() => setClosing(session.id)}>Завершить</button>
            )}
          </div>
        ))}
      </section>
      {closing ? (
        <div className="dialog-backdrop" role="presentation">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="close-session-title">
            <h3 id="close-session-title" className="card-title">Завершить сессию?</h3>
            <p>Этот вход перестанет действовать.</p>
            <div className="row">
              <button className="button danger" type="button" disabled={pending} onClick={closeSession}>Завершить</button>
              <button className="button secondary" type="button" onClick={() => setClosing(null)}>Отмена</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
