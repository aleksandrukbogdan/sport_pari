import Link from "next/link";

import { NewsListCard } from "@/modules/cards";
import { reasonLabel } from "@/shared/labels";
import { loadNews, loadRecommendations, loadViewer } from "@/shared/server-api";
import { EmptyState, ErrorState, PageTitle } from "@/shared/ui";

export default async function NewsPage({ searchParams }: { searchParams: Promise<{ sport_id?: string }> }) {
  const params = await searchParams;
  const sportId = params.sport_id ?? "";
  const [feed, viewer] = await Promise.all([loadNews(sportId || undefined), loadViewer()]);
  const recommendations = viewer ? await loadRecommendations() : null;
  return (
    <div className="stack">
      <PageTitle title="Новости">
        <p className="lead">Прочитайте материал и отметьте дату: от неё зависит, насколько факт ещё актуален.</p>
      </PageTitle>
      <form className="row" method="get">
        <label className="field">
          <span>Вид спорта</span>
          <input name="sport_id" defaultValue={sportId} placeholder="football" />
        </label>
        <button className="button secondary" type="submit">Показать</button>
        {sportId ? <Link href="/news">Сбросить фильтр</Link> : null}
      </form>
      {!feed.ok ? <ErrorState message={feed.message} href="/news" /> : feed.data.length === 0 ? (
        <EmptyState title={sportId ? "По выбранным фильтрам новостей нет" : "Новостей пока нет"} text="Измените фильтр или вернитесь позже." />
      ) : (
        <div className="cards news-grid">{feed.data.map((item) => <NewsListCard key={item.id} item={item} />)}</div>
      )}
      {recommendations?.ok && recommendations.data.length > 0 ? (
        <section>
          <h2 className="section-title">Для вас</h2>
          <ul>
            {recommendations.data.map((item) => (
              <li key={item.news_id}><Link href={`/news/${item.news_id}`}>Материал {item.news_id}</Link> · {reasonLabel(item.reason)}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
