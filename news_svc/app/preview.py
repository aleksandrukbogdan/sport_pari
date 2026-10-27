from html import escape
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import CommentRepo, NewsRepo
from app.api.recommendations import Recommendations, ViewRepo
from app.comments.models import Comment
from app.recommendations.models import NewsView

router = APIRouter(include_in_schema=False)


def _page(title: str, body: str) -> HTMLResponse:
    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem auto; max-width: 40rem; line-height: 1.4; }}
    a {{ color: inherit; }}
    article {{ border-top: 1px solid #ccc; padding: 0.8rem 0; }}
    form {{ margin-top: 1rem; }}
    textarea {{ width: 100%; min-height: 5rem; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""
    return HTMLResponse(document)


@router.get("/preview", response_class=HTMLResponse)
async def preview(news: NewsRepo, recommendations: Recommendations, user_id: str = "demo") -> HTMLResponse:
    rows = await news.list_published(sport_id=None, limit=20, offset=0)
    picks = await recommendations.for_user(user_id, limit=10)
    cards = []
    for item in rows:
        article, count = item
        href = f"/preview/news/{article.id}?user_id={quote(user_id)}"
        cards.append(
            "<article>"
            f"<h2><a href=\"{href}\">{escape(article.title)}</a></h2>"
            f"<p>{escape(article.summary)}</p>"
            f"<p>{escape(article.sport_id)} · комментариев: {count}</p>"
            "</article>"
        )
    pick_lines = "".join(
        f"<li><a href=\"/preview/news/{item.news_id}?user_id={quote(user_id)}\">"
        f"#{item.news_id}</a> · {escape(item.reason)} · {item.score}</li>"
        for item in picks
    )
    feed = "".join(cards) or "<p>Лента пустая. Запустите python -m app.seed.</p>"
    body = (
        f"<h1>Новости</h1>"
        f"<p>Пользователь: {escape(user_id)}</p>"
        f"<h2>Рекомендации</h2><ul>{pick_lines}</ul>"
        f"<h2>Лента</h2>{feed}"
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
        f"<p><a href=\"/preview?user_id={quote(user_id)}\">К ленте</a></p>"
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
