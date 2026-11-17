import Link from "next/link";

import { CommentForm } from "@/modules/forms";
import { loadArticle, loadComments, loadViewer } from "@/shared/server-api";
import { Breadcrumbs, EmptyState, ErrorState, PageTitle, WhenText } from "@/shared/ui";

export default async function ArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [article, comments, viewer] = await Promise.all([loadArticle(id), loadComments(id), loadViewer()]);
  if (!article.ok) {
    return (
      <div className="stack">
        <Breadcrumbs items={[{ href: "/news", label: "Новости" }, { label: "Материал" }]} />
        <ErrorState message={article.message} href="/news" />
      </div>
    );
  }
  return (
    <article className="stack article">
      <Breadcrumbs items={[{ href: "/news", label: "Новости" }, { label: article.data.title }]} />
      <PageTitle title={article.data.title}>
        <p className="muted"><WhenText value={article.data.published_at} /> · {article.data.sport_id}</p>
      </PageTitle>
      <p>{article.data.body}</p>
      <section className="stack">
        <h2 className="section-title">Комментарии · {comments.ok ? comments.data.length : 0}</h2>
        {!comments.ok ? <ErrorState message={comments.message} href={`/news/${id}`} /> : comments.data.length === 0 ? (
          <EmptyState title="Комментариев пока нет" text="Первый комментарий может начать разбор." />
        ) : (
          <ul className="stack">
            {comments.data.map((comment) => (
              <li className="surface" key={comment.id}>
                <p>{comment.body}</p>
                <p className="meta"><WhenText value={comment.created_at} /></p>
              </li>
            ))}
          </ul>
        )}
        {viewer ? <CommentForm newsId={article.data.id} demo={viewer.demo || article.demo} /> : <Link className="button secondary" href={`/login?next=/news/${id}`}>Войти, чтобы оставить комментарий</Link>}
      </section>
    </article>
  );
}
