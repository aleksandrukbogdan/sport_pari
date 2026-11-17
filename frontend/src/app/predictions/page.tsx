import Link from "next/link";

import { QuestionCard } from "@/modules/cards";
import { loadQuestions, loadViewer } from "@/shared/server-api";
import { EmptyState, ErrorState, PageTitle } from "@/shared/ui";

export default async function PredictionsPage({ searchParams }: { searchParams: Promise<{ kind?: string }> }) {
  const params = await searchParams;
  const kind = params.kind ?? "";
  const viewer = await loadViewer();
  const questions = await loadQuestions(kind || undefined, Boolean(viewer));
  return (
    <div className="stack">
      <PageTitle title="Прогнозы">
        <p className="lead">Ответьте «да» или «нет». Шкала на странице вопроса — распределение ответов участников, а не вероятность исхода.</p>
      </PageTitle>
      <div className="tabs">
        <Link href="/predictions" aria-current={!kind ? "page" : undefined}>Все</Link>
        <Link href="/predictions?kind=match" aria-current={kind === "match" ? "page" : undefined}>Матчи</Link>
        <Link href="/predictions?kind=event" aria-current={kind === "event" ? "page" : undefined}>События</Link>
      </div>
      {viewer?.isAdmin ? <Link className="button primary" href="/predictions/new">Создать вопрос</Link> : null}
      {!questions.ok ? <ErrorState message={questions.message} href="/predictions" /> : questions.data.length === 0 ? (
        <EmptyState title="Вопросов нет" text={kind ? "По выбранному типу вопросов нет." : "Администратор ещё не создал вопрос."} />
      ) : (
        <div className="cards">{questions.data.map((question) => <QuestionCard key={question.id} question={question} />)}</div>
      )}
    </div>
  );
}
