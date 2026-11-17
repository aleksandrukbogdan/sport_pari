import Link from "next/link";

import { matchStatusLabel, outcomeLabel, questionStatusLabel } from "@/shared/labels";
import type { MatchItem, NewsCard, QuestionItem } from "@/shared/types";
import { StatusBadge, WhenText } from "@/shared/ui";

export function NewsListCard({ item }: { item: NewsCard }) {
  return (
    <article className="card news">
      {item.image_url ? (
        <a className="news-figure" href={`/news/${item.id}`}>
          <img src={item.image_url} alt="" />
        </a>
      ) : null}
      <div className="news-body">
        <p className="news-kicker">
          <span className="sport-chip">{item.sport_id}</span>
          <WhenText value={item.published_at} />
        </p>
        <h3><Link className="news-title" href={`/news/${item.id}`}>{item.title}</Link></h3>
        <p className="news-summary">{item.summary}</p>
        <p className="meta-row">
          <span>комментариев {item.comments_count}</span>
          {item.source_name ? <span>{item.source_name}</span> : null}
        </p>
      </div>
    </article>
  );
}

export function MatchCard({ match, href }: { match: MatchItem; href?: string }) {
  const showScore = match.status === "live" || match.status === "finished";
  return (
    <article className="card match">
      <div className="row">
        <StatusBadge status={match.status} label={matchStatusLabel(match.status)} />
        <span className="meta">Учебный пример</span>
      </div>
      <h3 className="fixture">
        {href ? (
          <Link className="fixture-link" href={href}>
            <span className="team">{match.home.name}</span>
            <span className="fixture-mark" aria-hidden="true">—</span>
            <span className="team away">{match.away.name}</span>
          </Link>
        ) : (
          <span className="fixture-link">
            <span className="team">{match.home.name}</span>
            <span className="fixture-mark" aria-hidden="true">—</span>
            <span className="team away">{match.away.name}</span>
          </span>
        )}
      </h3>
      <p className="meta-row">
        <WhenText value={match.starts_at} />
        <span>сезон {match.season_id}</span>
      </p>
      {showScore && match.score ? <p className="score">{match.score.home}:{match.score.away}</p> : <p className="muted">Счёт появится после начала матча.</p>}
    </article>
  );
}

export function QuestionCard({ question }: { question: QuestionItem }) {
  return (
    <article className="card question">
      <div className="row">
        <StatusBadge status={question.status} label={questionStatusLabel(question.status)} />
        {question.my_choice ? <span className="muted">Ваш ответ: {question.my_choice === "yes" ? "Да" : "Нет"}</span> : null}
      </div>
      <h3 className="question-title"><Link href={`/predictions/${question.id}`}>{question.title}</Link></h3>
      {question.home_name && question.away_name ? (
        <p className="fixture-quiet">
          <span>{question.home_name}</span>
          <span aria-hidden="true">—</span>
          <span className="away">{question.away_name}</span>
        </p>
      ) : null}
      <p className="meta">Голосов: {question.yes + question.no}</p>
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
