import { redirect } from "next/navigation";

import { QuestionForm } from "@/modules/forms";
import { loadMatches, loadViewer } from "@/shared/server-api";
import { Breadcrumbs, ErrorState, PageTitle } from "@/shared/ui";

export default async function NewQuestionPage() {
  const viewer = await loadViewer();
  if (!viewer) redirect("/login?next=/predictions/new");
  if (!viewer.isAdmin) {
    return (
      <div className="stack">
        <PageTitle title="Создание вопроса" />
        <ErrorState message="Создавать вопросы может только администратор." href="/predictions" />
      </div>
    );
  }
  const matches = await loadMatches();
  return (
    <div className="stack">
      <Breadcrumbs items={[{ href: "/predictions", label: "Прогнозы" }, { label: "Новый вопрос" }]} />
      <PageTitle title="Новый вопрос">
        <p className="muted">Вопрос про матч сохранится, только если prediction уже получил событие этого матча.</p>
      </PageTitle>
      {!matches.ok ? <ErrorState message={matches.message} href="/predictions/new" /> : (
        <QuestionForm matches={matches.data} demo={viewer.demo} />
      )}
    </div>
  );
}
