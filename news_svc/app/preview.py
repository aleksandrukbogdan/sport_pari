from html import escape
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import CommentRepo, NewsRepo
from app.api.recommendations import Recommendations, ViewRepo
from app.comments.models import Comment
from app.recommendations.models import NewsView

router = APIRouter(include_in_schema=False)
_SPORT_LABELS = {"football": "Футбол", "hockey": "Хоккей", "tennis": "Теннис"}


def _page(title: str, body: str) -> HTMLResponse:
    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f6fa; color: #172033; line-height: 1.5; }}
    main {{ max-width: 70rem; margin: auto; padding: 2rem 1rem; }}
    h1, h2, h3, p {{ margin: 0 0 .65rem; }}
    a {{ color: #174e9e; }}
    .panels {{ display: grid; grid-template-columns: 3fr 2fr; gap: 1rem; align-items: start; }}
    section {{ background: white; border: 1px solid #d7deea; border-radius: .75rem; padding: 1rem; }}
    article, li {{ border-top: 1px solid #d7deea; padding: .75rem 0; }}
    ol {{ padding-inline-start: 1.75rem; margin-bottom: 0; }}
    .meta {{ color: #465674; font-size: .9rem; }}
    .badge {{ display: inline-block; padding: .15rem .5rem; border-radius: .4rem; background: #eaf0fb; }}
    .seen {{ background: #edf0f3; }}
    nav {{ display: flex; flex-wrap: wrap; gap: .5rem; margin: 1rem 0; }}
    nav a, button {{ background: white; border: 1px solid #bbc9e0; border-radius: .45rem; padding: .45rem .7rem; }}
    nav a[aria-current="page"] {{ background: #174e9e; color: white; }}
    form {{ max-width: 35rem; margin-top: 1rem; }}
    textarea {{ box-sizing: border-box; width: 100%; min-height: 5rem; }}
    @media (max-width: 46rem) {{ .panels {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>{body}</main>
</body>
</html>"""
    return HTMLResponse(document, headers={"Cache-Control": "no-store"})


def _sport_label(sport_id: str) -> str:
    return escape(_SPORT_LABELS.get(sport_id, sport_id))


def _profile_picker(profiles: dict[str, str], user_id: str) -> str:
    links = []
    for profile_id, label in profiles.items():
        current = ' aria-current="page"' if profile_id == user_id else ""
        links.append(f'<a href="/preview?user_id={quote(profile_id, safe="")}"{current}>{escape(label)}</a>')
    return '<nav aria-label="Демо-профили">' + "".join(links) + "</nav>"


@router.get("/preview", response_class=HTMLResponse)
async def preview(
    request: Request, news: NewsRepo, recommendations: Recommendations, user_id: str = "demo",
) -> HTMLResponse:
    rows = await news.list_published(sport_id=None, limit=20, offset=0)
    picks = await recommendations.rank_for_user(user_id, limit=10)
    user_query = quote(user_id, safe="")
    profiles = getattr(request.app.state, "preview_profiles", {})
    profile_label = profiles.get(user_id, user_id)
    picker = _profile_picker(profiles, user_id) if profiles else ""
    cards = []
    for article, count in rows:
        href = f"/preview/news/{article.id}?user_id={user_query}"
        cards.append(
            "<article>"
            f'<h3><a href="{href}">{escape(article.title)}</a></h3>'
            f"<p>{escape(article.summary)}</p>"
            f'<p class="meta">{_sport_label(article.sport_id)} · комментариев {count}</p>'
            "</article>"
        )

    pick_lines = []
    for pick in picks:
        article = pick.news
        reason = "По интересам" if pick.recommendation.reason == "sport" else "По популярности и свежести"
        seen_badge = '<span class="badge seen">Открыто</span>' if pick.seen else '<span class="badge">Новое</span>'
        href = f"/preview/news/{article.id}?user_id={user_query}"
        pick_lines.append(
            f'<li><h3><a href="{href}">{escape(article.title)}</a></h3>'
            f'<p class="meta">{_sport_label(article.sport_id)} · {reason} · {seen_badge}</p>'
            f'<p class="meta">Оценка {pick.recommendation.score:.3f} · вес просмотров {pick.popularity:.3f}</p></li>'
        )
    ranked = f'<ol>{"".join(pick_lines)}</ol>' if pick_lines else "<p>Пока нет рекомендаций.</p>"
    feed = "".join(cards) or "<p>Лента пустая. Запустите python -m app.seed.</p>"
    body = (
        "<h1>Новостная лента</h1>"
        f'<p class="meta">Профиль · {escape(profile_label)}</p>{picker}'
        '<div class="panels">'
        '<section aria-labelledby="recommendations"><h2 id="recommendations">Рекомендации</h2>'
        "<p>Откройте статью и вернитесь к рекомендациям. Она будет отмечена как открытая и опустится ниже новых.</p>"
        f"{ranked}</section>"
        f'<section aria-labelledby="feed"><h2 id="feed">Лента по дате публикации</h2>{feed}</section></div>'
    )
    return _page("Новости", body)


@router.get("/preview/news/{news_id}", response_class=HTMLResponse)
async def preview_article(
    news_id: int,
    news: NewsRepo,
    comments: CommentRepo,
    views: ViewRepo,
    user_id: str = "demo",
) -> HTMLResponse:
    row = await news.get(news_id)
    if row is None:
        return _page("Нет материала", "<p>Материал не найден.</p><p><a href=\"/preview\">К ленте</a></p>")
    article, count = row
    await views.add(NewsView(user_id=user_id, news_id=news_id))
    thread = await comments.list_for_news(news_id, limit=50, offset=0)
    rendered_comments = "".join(
        f"<article><p>{escape(item.author_id)}</p><p>{escape(item.body)}</p></article>"
        for item in thread
    ) or "<p>Комментариев пока нет.</p>"
    body = (
        f'<p><a href="/preview?user_id={quote(user_id, safe="")}">К рекомендациям и ленте</a></p>'
        f"<h1>{escape(article.title)}</h1>"
        f"<p>{escape(article.summary)}</p>"
        f"<p>{escape(article.body)}</p>"
        f"<p>Комментариев: {count}</p>"
        f"<h2>Комментарии</h2>{rendered_comments}"
        f"<form method=\"post\" action=\"/preview/news/{news_id}/comments\">"
        f"<input type=\"hidden\" name=\"user_id\" value=\"{escape(user_id)}\">"
        f"<textarea name=\"body\" required></textarea>"
        f"<button type=\"submit\">Отправить</button>"
        f"</form>"
    )
    return _page(article.title, body)


@router.post("/preview/news/{news_id}/comments")
async def preview_comment(
    news_id: int,
    comments: CommentRepo,
    user_id: Annotated[str, Form()],
    body: Annotated[str, Form()],
) -> RedirectResponse:
    text = body.strip()
    author = user_id.strip()
    if text and author:
        await comments.add(Comment(news_id=news_id, author_id=author, body=text))
    return RedirectResponse(
        f"/preview/news/{news_id}?user_id={quote(author or user_id)}",
        status_code=303,
    )
