import Link from "next/link";

import { MatchCard } from "@/modules/cards";
import { loadMatches, loadStandings } from "@/shared/server-api";
import { EmptyState, ErrorState, PageTitle } from "@/shared/ui";

export default async function MatchesPage({ searchParams }: { searchParams: Promise<{ season_id?: string }> }) {
  const params = await searchParams;
  const seasonId = params.season_id ?? "1";
  const [matches, table] = await Promise.all([loadMatches(seasonId), loadStandings(seasonId)]);
  return (
    <div className="stack">
      <PageTitle title="Матчи и статистика">
        <p className="muted">Учебный пример. Данные вымышленные, это не прямая трансляция.</p>
      </PageTitle>
      <form className="row" method="get">
        <label className="field">
          <span>Сезон</span>
          <input name="season_id" defaultValue={seasonId} inputMode="numeric" />
        </label>
        <button className="button secondary" type="submit">Показать</button>
      </form>
      {!matches.ok ? <ErrorState message="Не удалось загрузить матчи. Попробуйте ещё раз." href="/matches" /> : matches.data.length === 0 ? (
        <EmptyState title="По выбранным фильтрам матчей нет" text="Проверьте номер сезона." />
      ) : (
        <div className="cards two">{matches.data.map((match) => <MatchCard key={match.match_id} match={match} href={`/matches/${match.match_id}`} />)}</div>
      )}
      <section>
        <h2 className="section-title">Турнирная таблица</h2>
        {!table.ok ? <ErrorState message={table.message} href="/matches" /> : table.data.length === 0 ? <EmptyState title="Таблицы нет" text="Для сезона пока нет команд." /> : (
          <div className="table-wrap">
            <table>
              <caption className="meta">И — игры, В — победы, Н — ничьи, П — поражения, М — мячи, Р — разница, О — очки</caption>
              <thead>
                <tr>
                  <th className="num">Место</th><th>Команда</th><th className="num">И</th><th className="num">В</th><th className="num">Н</th><th className="num">П</th><th className="num">М</th><th className="num">Р</th><th className="num">О</th>
                </tr>
              </thead>
              <tbody>
                {table.data.map((row) => (
                  <tr key={row.team_id}>
                    <td className="num">{row.position ?? "—"}</td>
                    <td><Link href={`/matches?season_id=${seasonId}`}>{row.team_name}</Link></td>
                    <td className="num">{row.played}</td>
                    <td className="num">{row.wins}</td>
                    <td className="num">{row.draws}</td>
                    <td className="num">{row.losses}</td>
                    <td className="num">{row.goals_for}:{row.goals_against}</td>
                    <td className="num">{row.goal_difference}</td>
                    <td className="num">{row.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
