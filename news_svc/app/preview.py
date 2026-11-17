import re
from math import ceil
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import CommentRepo, NewsRepo, get_user_service
from app.api.recommendations import Recommendations, ViewRepo
from app.clients.user_service import UserInterests, UserServiceClient
from app.comments.models import Comment
from app.recommendations.models import NewsView
from app.ui import SPORTS, templates

router = APIRouter(include_in_schema=False)
PAGE_SIZE = 12
Users = Annotated[UserServiceClient, Depends(get_user_service)]


def safe_return(value: str | None) -> str:
    if not value:
        return "/preview"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "/preview"
    if (
        parsed.scheme
        or parsed.netloc
        or "\\" in value
        or any(ord(char) < 32 for char in value)
    ):
        return "/preview"
    if parsed.path == "/preview" or re.fullmatch(r"/preview/news/\d+", parsed.path):
        return value
    return "/preview"


def link(path: str, **values) -> str:
    query = urlencode(
        {
            key: value
            for key, value in values.items()
            if value is not None and value != ""
        }
    )
    return path + ("?" + query if query else "")


def guest_link(target):
    parsed = urlsplit(safe_return(target))
    if parsed.path == "/preview":
        params = dict(parse_qsl(parsed.query))
        params["view"] = "all"
        return link("/preview", **params)
    return safe_return(target)


def context(
    request: Request, user_id: str = "anonymous", target: str = "/preview", **values
):
    profiles = getattr(request.app.state, "preview_profiles", {})
    profile = getattr(request.state, "preview_profile", {})
    name = profiles.get(user_id, profile.get("username", user_id))
    return dict(
        request=request,
        user_id=user_id,
        username=name if user_id != "anonymous" else "Гость",
        profile_url=link(
            "/preview/profile",
            return_to=safe_return(target),
            user_id=user_id if profiles else None,
        ),
        demo=bool(profiles),
        profiles=profiles,
        sports=SPORTS,
        success=None,
        error=None,
        guest_url=guest_link(target),
        **values,
    )


def render(request, template, data, status_code=200):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=data,
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


def error_response(request, title, message, *, status_code=503, retry_url="/preview"):
    data = context(
        request, title=title, message=message, retry_url=safe_return(retry_url)
    )
    return render(request, "error.html", data, status_code)


async def preview_user(request: Request, users: Users, user_id: str = "demo") -> str:
    if getattr(request.app.state, "preview_profiles", None):
        return user_id
    token = request.cookies.get("preview_token")
    if token:
        try:
            profile = await users.profile(f"Bearer {token}")
        except HTTPException as error:
            if error.status_code in (401, 403, 404):
                request.state.session_expired = True
                return "anonymous"
            raise
        request.state.preview_profile = profile
        return profile["id"]
    return "anonymous"


PreviewUser = Annotated[str, Depends(preview_user)]


def signed_in_response(request: Request, token: str, return_to: str):
    response = RedirectResponse(safe_return(return_to), status_code=303)
    response.set_cookie(
        "preview_token",
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=1800,
        path="/preview",
    )
    return response


@router.post("/preview/login")
async def preview_login(
    request: Request,
    users: Users,
    username: Annotated[str, Form(min_length=1, max_length=255)],
    password: Annotated[str, Form(min_length=1, max_length=1000)],
    return_to: Annotated[str, Form()] = "/preview",
):
    try:
        token = await users.login(username.strip(), password)
        await users.profile(f"Bearer {token}")
    except HTTPException as error:
        message = "Не удалось войти. Проверьте имя пользователя и пароль."
        if error.status_code == 403:
            message = "Вход требует подтверждения или обновления учётной записи в пользовательском сервисе."
        elif error.status_code == 429:
            message = "Слишком много попыток входа. Попробуйте позднее."
        elif error.status_code >= 500:
            message = "Сервис входа временно недоступен. Попробуйте ещё раз."
        data = context(
            request,
            target=safe_return(return_to),
            title="Вход",
            active="profile",
            return_to=safe_return(return_to),
            login_username=username,
        )
        data["error"] = message
        return render(request, "news/profile.html", data, error.status_code)
    return signed_in_response(request, token, return_to)


@router.post("/preview/session")
async def preview_session(
    request: Request,
    token: Annotated[str, Form()],
    users: Users,
    return_to: Annotated[str, Form()] = "/preview",
):
    await users.profile(f"Bearer {token}")
    return signed_in_response(request, token, return_to)


@router.post("/preview/logout")
async def preview_logout():
    response = RedirectResponse("/preview", status_code=303)
    response.delete_cookie("preview_token", path="/preview")
    return response


@router.get("/preview/profile", response_class=HTMLResponse)
async def preview_profile(
    request: Request,
    users: Users,
    user_id: PreviewUser,
    return_to: str = "/preview",
    saved: bool = False,
):
    data = context(
        request,
        user_id,
        return_to,
        title="Настройки ленты",
        active="profile",
        return_to=safe_return(return_to),
        login_username="",
    )
    if user_id != "anonymous":
        interests = await users.get_interests(user_id)
        data.update(
            interest_sports=interests.sport_ids if interests else [],
            team_ids=interests.team_ids if interests else [],
            interests_available=interests is not None and not data["demo"],
        )
        if interests:
            data["sports"] = {
                **SPORTS,
                **{
                    sport: sport for sport in interests.sport_ids if sport not in SPORTS
                },
            }
    if saved:
        data["success"] = (
            "Интересы сохранены. Персональная лента обновится при следующем открытии."
        )
    elif getattr(request.state, "session_expired", False):
        data["error"] = "Сессия истекла. Войдите ещё раз, чтобы продолжить."
    return render(request, "news/profile.html", data)


@router.post("/preview/interests")
async def preview_interests(
    request: Request,
    users: Users,
    sport_ids: Annotated[str, Form(max_length=13000)] = "",
    team_ids: Annotated[str, Form(max_length=13000)] = "",
    return_to: Annotated[str, Form()] = "/preview",
):
    token = request.cookies.get("preview_token")
    if not token:
        return RedirectResponse(
            link("/preview/profile", return_to=safe_return(return_to)), status_code=303
        )
    form = await request.form()
    profile = None
    existing = None
    try:
        if form.get("format") == "checkboxes":
            profile = await users.profile(f"Bearer {token}")
            existing = await users.get_interests(profile["id"])
            if existing is None:
                raise HTTPException(503, "Interests unavailable")
            interests = UserInterests(
                sport_ids=form.getlist("sports"), team_ids=existing.team_ids
            )
        else:
            interests = UserInterests(
                sport_ids=[
                    value.strip() for value in sport_ids.split(",") if value.strip()
                ],
                team_ids=[
                    value.strip() for value in team_ids.split(",") if value.strip()
                ],
            )
        await users.authorized_request(
            "PUT", "/user/interests", f"Bearer {token}", json=interests.model_dump()
        )
    except (HTTPException, ValueError) as error:
        if form.get("format") == "checkboxes":
            if profile:
                request.state.preview_profile = profile
            data = context(
                request,
                profile["id"] if profile else "anonymous",
                safe_return(return_to),
                title="Настройки ленты",
                active="profile",
                return_to=safe_return(return_to),
                login_username="",
                interest_sports=form.getlist("sports"),
                team_ids=existing.team_ids if existing else [],
                interests_available=profile is not None,
            )
            data["error"] = (
                "Не удалось сохранить интересы. Ваш выбор сохранён в форме. Попробуйте ещё раз."
                if profile
                else "Сессия истекла или сервис входа недоступен. Войдите в профиль ещё раз."
            )
            return render(
                request,
                "news/profile.html",
                data,
                error.status_code if isinstance(error, HTTPException) else 422,
            )
        data = context(
            request,
            title="Не удалось сохранить интересы",
            message="Профиль временно недоступен или сессия истекла. Вернитесь к настройкам и повторите сохранение.",
            retry_url=safe_return(return_to),
        )
        return render(request, "error.html", data, 503)
    if form.get("format") == "checkboxes":
        return RedirectResponse(
            link("/preview/profile", saved=1, return_to=safe_return(return_to)),
            status_code=303,
        )
    return RedirectResponse(safe_return(return_to), status_code=303)


def card(article, comments_count, user_id, return_to, *, demo=False, rank=None):
    return {
        "article": article,
        "comments_count": comments_count,
        "href": link(
            f"/preview/news/{article.id}",
            user_id=user_id if demo else None,
            return_to=return_to,
        ),
        "rank": rank,
    }


@router.get("/preview", response_class=HTMLResponse)
async def preview(
    request: Request,
    news: NewsRepo,
    recommendations: Recommendations,
    user_id: PreviewUser,
    q: str | None = Query(default=None, max_length=200),
    sport_id: str | None = None,
    view: Literal["all", "for-you"] = "all",
    offset: int = Query(0, ge=0),
):
    q = (q or "").strip()
    sport_id = sport_id or None
    demo = bool(getattr(request.app.state, "preview_profiles", None))
    params = {
        "q": q,
        "sport_id": sport_id,
        "view": view,
        "user_id": user_id if demo else None,
    }
    current_url = link("/preview", **params, offset=offset if offset else None)
    if view == "for-you" and user_id == "anonymous":
        return RedirectResponse(
            link("/preview/profile", return_to=current_url), status_code=303
        )
    counts = await news.sport_counts()
    interests = (
        await recommendations.users.get_interests(user_id)
        if user_id != "anonymous"
        else None
    )
    # Ranking uses the same service as the public API. Filtering preserves its order.
    ranked = await recommendations.rank_for_user(
        user_id, limit=1000 if view == "for-you" else 10
    )
    if view == "for-you":
        ranked = [
            item
            for item in ranked
            if (not sport_id or item.news.sport_id == sport_id)
            and (
                not q
                or q.casefold() in f"{item.news.title} {item.news.body}".casefold()
            )
        ]
        total = len(ranked)
        cards = [
            card(
                item.news,
                item.comments_count,
                user_id,
                current_url,
                demo=demo,
                rank=item,
            )
            for item in ranked[offset : offset + PAGE_SIZE]
        ]
    else:
        total = await news.count_published(sport_id=sport_id, q=q)
        rows = await news.list_published(
            sport_id=sport_id, q=q, offset=offset, limit=PAGE_SIZE
        )
        cards = [
            card(article, count, user_id, current_url, demo=demo)
            for article, count in rows
        ]
    pages = max(1, ceil(total / PAGE_SIZE))
    if offset and offset >= total:
        return RedirectResponse(
            link(
                "/preview",
                **params,
                offset=(pages - 1) * PAGE_SIZE if pages > 1 else None,
            ),
            status_code=303,
        )
    data = context(
        request,
        user_id,
        current_url,
        title="Новости",
        view=view,
        cards=cards,
        total=total,
        recommendations=[
            card(
                item.news,
                item.comments_count,
                user_id,
                current_url,
                demo=demo,
                rank=item,
            )
            for item in ranked[:10]
        ],
        inventory_count=sum(counts.values()),
        sport_counts=counts,
        q=q,
        sport_id=sport_id,
        chips=[
            {
                "id": id,
                "label": SPORTS.get(id, id),
                "count": counts.get(id, 0),
                "href": link("/preview", **{**params, "sport_id": id}),
            }
            for id in SPORTS
            if counts.get(id)
        ],
        interest_sports=interests.sport_ids if interests else [],
        all_url=link("/preview", **{**params, "view": "all"}),
        personal_url=link("/preview", **{**params, "view": "for-you"}),
        clear_sport_url=link("/preview", **{**params, "sport_id": None}),
        reset_url=link("/preview", view=view, user_id=user_id if demo else None),
        previous_url=link("/preview", **params, offset=max(0, offset - PAGE_SIZE))
        if offset
        else None,
        next_url=link("/preview", **params, offset=offset + PAGE_SIZE)
        if offset + PAGE_SIZE < total
        else None,
        page=offset // PAGE_SIZE + 1,
        pages=pages,
    )
    return render(request, "news/feed.html", data)


async def article_response(
    request,
    news_id,
    news,
    comments,
    user_id,
    return_to,
    *,
    draft="",
    error=None,
    status=200,
    comment_offset=0,
):
    row = await news.get(news_id)
    if row is None:
        return error_response(
            request,
            "Материал не найден",
            "Возможно, публикация снята или адрес изменился. Вернитесь к новостям.",
            status_code=404,
        )
    article, count = row
    thread = await comments.list_for_news(news_id, limit=50, offset=comment_offset)
    demo = bool(getattr(request.app.state, "preview_profiles", None))
    next_comments = (
        link(
            f"/preview/news/{news_id}",
            return_to=return_to,
            comment_offset=comment_offset + 50,
            user_id=user_id if demo else None,
        )
        if comment_offset + 50 < count
        else None
    )
    data = context(
        request,
        user_id,
        link(f"/preview/news/{news_id}", return_to=return_to),
        title=article.title,
        article=article,
        comments_count=count,
        comments=thread,
        return_to=return_to,
        draft=draft,
        comments_next=next_comments,
    )
    data["error"] = error
    if request.query_params.get("comment") == "sent" and not error:
        data["success"] = "Комментарий опубликован."
    return render(request, "news/article.html", data, status)


@router.get("/preview/news/{news_id}", response_class=HTMLResponse)
async def preview_article(
    request: Request,
    news_id: int,
    news: NewsRepo,
    comments: CommentRepo,
    views: ViewRepo,
    user_id: PreviewUser,
    return_to: str = "/preview",
    comment_offset: int = Query(0, ge=0),
):
    if user_id != "anonymous" and await news.get(news_id) is not None:
        await views.add(NewsView(user_id=user_id, news_id=news_id))
    return await article_response(
        request,
        news_id,
        news,
        comments,
        user_id,
        safe_return(return_to),
        comment_offset=comment_offset,
    )


@router.post("/preview/news/{news_id}/comments")
async def preview_comment(
    request: Request,
    news_id: int,
    comments: CommentRepo,
    news: NewsRepo,
    authenticated_user: PreviewUser,
    user_id: Annotated[str, Form()],
    body: Annotated[str, Form()],
    return_to: Annotated[str, Form()] = "/preview",
):
    demo = bool(getattr(request.app.state, "preview_profiles", None))
    author = user_id.strip() if demo else authenticated_user
    article_url = link(
        f"/preview/news/{news_id}",
        user_id=author if demo else None,
        return_to=safe_return(return_to),
    )
    if author == "anonymous":
        return RedirectResponse(
            link("/preview/profile", return_to=article_url), status_code=303
        )
    text = body.strip()
    if not text or len(text) > 2000:
        return await article_response(
            request,
            news_id,
            news,
            comments,
            author,
            safe_return(return_to),
            draft=body,
            error="Введите комментарий от 1 до 2000 символов.",
            status=422,
        )
    await comments.add(Comment(news_id=news_id, author_id=author, body=text))
    return RedirectResponse(article_url + "&comment=sent#comments", status_code=303)


@router.get("/preview/components", response_class=HTMLResponse)
async def components_page(request: Request, news: NewsRepo, user_id: PreviewUser):
    rows = await news.list_published(sport_id=None, limit=1, offset=0)
    sample = (
        card(rows[0][0], rows[0][1], user_id, "/preview/components") if rows else None
    )
    return render(
        request,
        "components-page.html",
        context(request, user_id, title="Компоненты интерфейса", sample=sample),
    )
