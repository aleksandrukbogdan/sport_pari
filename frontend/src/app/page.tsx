import Link from "next/link";

import { MatchCard, NewsListCard, QuestionCard } from "@/modules/cards";
import { loadMatches, loadNews, loadQuestions } from "@/shared/server-api";
import { EmptyState, ErrorState, PageTitle } from "@/shared/ui";

export default async function OverviewPage() {
  const [news, matches, questions] = await Promise.all([loadNews(), loadMatches(), loadQuestions()]);
  return (
    <div className="stack">
      <PageTitle title="Обзор">
        <p className="lead muted">Читайте материал, смотрите статистику матча и отвечайте на вопрос. Доля голосов — это распределение ответов, а не вероятность исхода.</p>
      </PageTitle>
      <section>
        <div className="row">
          <h2 className="section-title">Актуальные новости</h2>
          <Link href="/news">Все новости</Link>
        </div>
        {!news.ok ? <ErrorState message={news.message} href="/" /> : news.data.length === 0 ? <EmptyState title="Новостей пока нет" text="Лента пуста." /> : (
          <div className="cards two">{news.data.slice(0, 2).map((item) => <NewsListCard key={item.id} item={item} />)}</div>
        )}
      </section>
      <section>
        <div className="row">
          <h2 className="section-title">Ближайшие матчи</h2>
          <Link href="/matches">Матчи и статистика</Link>
        </div>
        {!matches.ok ? <ErrorState message={matches.message} href="/" /> : matches.data.length === 0 ? <EmptyState title="Матчей нет" text="Сервис матчей не вернул список." /> : (
          <div className="cards two">{matches.data.slice(0, 2).map((match) => <MatchCard key={match.match_id} match={match} href={`/matches/${match.match_id}`} />)}</div>
        )}
      </section>
      <section>
        <div className="row">
          <h2 className="section-title">Доступные вопросы</h2>
          <Link href="/predictions">Прогнозы</Link>
        </div>
        {!questions.ok ? <ErrorState message={questions.message} href="/" /> : questions.data.length === 0 ? <EmptyState title="Вопросов пока нет" text="Когда администратор создаст вопрос, он появится здесь." /> : (
          <div className="cards two">{questions.data.slice(0, 2).map((question) => <QuestionCard key={question.id} question={question} />)}</div>
        )}
      </section>
    </div>
  );
}
