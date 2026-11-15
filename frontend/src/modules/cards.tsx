import Link from "next/link";

import { matchStatusLabel, outcomeLabel, questionStatusLabel } from "@/shared/labels";
import type { MatchItem, NewsCard, QuestionItem } from "@/shared/types";
import { StatusBadge, WhenText } from "@/shared/ui";

export function NewsListCard({ item }: { item: NewsCard }) {
  return (
    <article className="card">
      <h3 className="card-title"><Link href={`/news/${item.id}`}>{item.title}</Link></h3>
      <p>{item.summary}</p>
      <p className="muted"><WhenText value={item.published_at} /> · {item.sport_id} · комментариев {item.comments_count}</p>
    </article>
  );
}

export function MatchCard({ match, href }: { match: MatchItem; href?: string }) {
  const showScore = match.status === "live" || match.status === "finished";
  return (
    <article className="card">
      <div className="row">
        <StatusBadge status={match.status} label={matchStatusLabel(match.status)} />
        <span className="meta">Учебный пример</span>
      </div>
      <h3 className="card-title">
        {href ? <Link href={href}>{match.home.name} — {match.away.name}</Link> : `${match.home.name} — ${match.away.name}`}
      </h3>
      <p className="muted"><WhenText value={match.starts_at} /> · сезон {match.season_id}</p>
      {showScore && match.score ? <p className="score">{match.score.home}:{match.score.away}</p> : <p className="muted">Счёт появится после начала матча.</p>}
    </article>
  );
}

export function QuestionCard({ question }: { question: QuestionItem }) {
  return (
    <article className="card">
      <div className="row">
        <StatusBadge status={question.status} label={questionStatusLabel(question.status)} />
        {question.my_choice ? <span className="muted">Ваш ответ: {question.my_choice === "yes" ? "Да" : "Нет"}</span> : null}
      </div>
      <h3 className="card-title"><Link href={`/predictions/${question.id}`}>{question.title}</Link></h3>
      {question.home_name && question.away_name ? <p className="muted">{question.home_name} — {question.away_name}</p> : null}
      <p>Голосов: {question.yes + question.no}</p>
    </article>
  );
}

export function VoteShare({ yes, no, share }: { yes: number; no: number; share: number | null }) {
  const total = yes + no;
  if (total === 0 || share === null) return <p>Пока нет голосов.</p>;
  const yesPercent = Math.round(share * 100);
  const noPercent = 100 - yesPercent;
  return (
    <div>
      <h3 className="card-title">Распределение ответов участников</h3>
      <p>Да, {yesPercent}% · {yes}</p>
      <div className="bar-track" aria-hidden="true"><span className="bar-fill" style={{ width: `${yesPercent}%` }} /></div>
      <p>Нет, {noPercent}% · {no}</p>
      <div className="bar-track" aria-hidden="true"><span className="bar-fill no" style={{ width: `${noPercent}%` }} /></div>
      <table>
        <caption className="meta">Те же доли в таблице</caption>
        <thead><tr><th>Ответ</th><th className="num">Голоса</th><th className="num">Доля</th></tr></thead>
        <tbody>
          <tr><td>Да</td><td className="num">{yes}</td><td className="num">{yesPercent}%</td></tr>
          <tr><td>Нет</td><td className="num">{no}</td><td className="num">{noPercent}%</td></tr>
        </tbody>
      </table>
    </div>
  );
}

export function OutcomeNote({ outcome }: { outcome: string | null }) {
  if (!outcome) return null;
  return <p>Итог матча: {outcomeLabel(outcome)}. Это факт матча, а не оценка вашего ответа.</p>;
}
