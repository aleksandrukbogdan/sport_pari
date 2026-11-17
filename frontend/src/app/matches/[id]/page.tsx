import Link from "next/link";

import { MatchCard } from "@/modules/cards";
import { loadHeadToHead, loadMatch, loadQuestions, loadTeamStats } from "@/shared/server-api";
import { Breadcrumbs, EmptyState, ErrorState, PageTitle } from "@/shared/ui";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const match = await loadMatch(id);
  if (!match.ok) {
    return (
      <div className="stack">
        <Breadcrumbs items={[{ href: "/matches", label: "Матчи и статистика" }, { label: "Матч" }]} />
        <ErrorState message={match.message} href="/matches" />
      </div>
    );
  }
  const season = String(match.data.season_id);
  const [home, away, meetings, questions] = await Promise.all([
    loadTeamStats(String(match.data.home.id), season),
    loadTeamStats(String(match.data.away.id), season),
    loadHeadToHead(id),
    loadQuestions("match"),
  ]);
  const related = questions.ok ? questions.data.filter((item) => item.match_external_id === id) : [];
  return (
    <div className="stack">
      <Breadcrumbs items={[{ href: "/matches", label: "Матчи и статистика" }, { label: `${match.data.home.name} — ${match.data.away.name}` }]} />
      <PageTitle title={`${match.data.home.name} — ${match.data.away.name}`} />
      <MatchCard match={match.data} />
      <section>
        <h2 className="section-title">Статистика сезона</h2>
        <div className="cards two">
          <StatsBlock title={match.data.home.name} result={home} />
          <StatsBlock title={match.data.away.name} result={away} />
        </div>
      </section>
      <section>
        <h2 className="section-title">Последние личные встречи</h2>
        <HeadToHeadBlock result={meetings} home={match.data.home.name} away={match.data.away.name} />
      </section>
      <section>
        <h2 className="section-title">Связанные вопросы</h2>
        {related.length === 0 ? <EmptyState title="Связанных вопросов нет" text="Вопрос появится здесь, если он создан для этого матча." /> : (
          <ul>{related.map((item) => <li key={item.id}><Link href={`/predictions/${item.id}`}>{item.title}</Link></li>)}</ul>
        )}
      </section>
    </div>
  );
}

function StatsBlock({ title, result }: { title: string; result: Awaited<ReturnType<typeof loadTeamStats>> }) {
  if (!result.ok) return <ErrorState message={`${title}: ${result.message}`} />;
  const row = result.data;
  const labels = { win: "Победа", draw: "Ничья", loss: "Поражение" } as const;
  return (
    <div className="surface">
      <h3 className="card-title">{title}</h3>
      <p>Игры {row.played}, победы {row.wins}, ничьи {row.draws}, поражения {row.losses}.</p>
      <p>Мячи {row.goals_for}:{row.goals_against}, очки {row.points}.</p>
      {row.recent_form && (
        <p className="meta">
          Последние игры (сначала свежие): {row.recent_form.length
            ? row.recent_form.map((outcome) => labels[outcome]).join(" · ")
            : "нет завершённых матчей"}
        </p>
      )}
      <p className="meta">Сезон {row.season_id ?? ""}. Единица очков — очко за матч сезона.</p>
    </div>
  );
}

function HeadToHeadBlock({ result, home, away }: {
  result: Awaited<ReturnType<typeof loadHeadToHead>>;
  home: string;
  away: string;
}) {
  if (!result.ok) return <ErrorState message={result.message} />;
  const { matches, summary } = result.data;
  if (!matches.length) {
    return <EmptyState title="Нет личных встреч" text="В данных сервиса нет завершённых встреч этой пары до текущего матча." />;
  }
  return (
    <div className="surface">
      {result.demo && <p className="meta">Демонстрационные данные</p>}
      <ul>
        {matches.map((match) => (
          <li key={match.match_id}>
            {new Date(match.starts_at).toLocaleDateString("ru-RU", { timeZone: "UTC" })} ·{" "}
            {match.home.name} {match.score?.home}:{match.score?.away} {match.away.name}
          </li>
        ))}
      </ul>
      <p className="meta">
        Победы «{home}»: {summary.home_wins} · Ничьи: {summary.draws} · Победы «{away}»: {summary.away_wins}
      </p>
    </div>
  );
}
