import Link from "next/link";

import { MatchCard, OutcomeNote, VoteShare } from "@/modules/cards";
import { VoteForm } from "@/modules/forms";
import { matchStatusLabel } from "@/shared/labels";
import { loadMatch, loadQuestion, loadViewer } from "@/shared/server-api";
import { Breadcrumbs, ErrorState, PageTitle, StatusBadge, WhenText } from "@/shared/ui";

export default async function QuestionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [question, viewer] = await Promise.all([loadQuestion(id), loadViewer()]);
  if (!question.ok) {
    return (
      <div className="stack">
        <Breadcrumbs items={[{ href: "/predictions", label: "Прогнозы" }, { label: "Вопрос" }]} />
        <ErrorState message={question.message} href="/predictions" />
      </div>
    );
  }
  const item = question.data;
  const match = item.match_external_id ? await loadMatch(item.match_external_id) : null;
  return (
    <div className="stack">
      <Breadcrumbs items={[{ href: "/predictions", label: "Прогнозы" }, { label: item.title }]} />
      <PageTitle title={item.title}>
        <StatusBadge status={item.status} label={item.status === "open" ? "Открыт" : item.status === "closed" ? "Закрыт" : "Снят"} />
      </PageTitle>
      {match?.ok ? <MatchCard match={match.data} href={`/matches/${match.data.match_id}`} /> : item.home_name ? (
        <div className="card">
          <p className="card-title">{item.home_name} — {item.away_name}</p>
          {item.starts_at ? <p className="muted"><WhenText value={item.starts_at} /></p> : null}
          {item.match_status ? <StatusBadge status={item.match_status} label={matchStatusLabel(item.match_status)} /> : null}
        </div>
      ) : null}
      <section className="surface stack">
        {viewer ? <VoteForm question={item} demo={viewer.demo || question.demo} /> : <p><Link href={`/login?next=/predictions/${id}`}>Войдите, чтобы отправить прогноз.</Link></p>}
        {item.status !== "open" ? <p>Голосование закрыто.</p> : null}
        <VoteShare yes={item.yes} no={item.no} share={item.yes_share} />
        <OutcomeNote outcome={item.factual_outcome} />
      </section>
    </div>
  );
}
