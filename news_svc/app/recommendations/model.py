class NewsRanker:
    """Оценка свежего окна материалов для одного пользователя.

    Как библиотекарь с двумя списками: что этот человек уже читал и что зал
    читает на этой неделе. Общие имена команд и турниров поднимают материал.
    Вчерашняя громкая новость тускнеет.

    score = W_POPULARITY * decayed_popularity
          + W_CONTENT * cosine(user_text, article_text)
          + W_SPORT * sport_match

    Похожесть текста: sklearn TfidfVectorizer по заголовку и телу, затем
    cosine_similarity. В спортивных новостях много редких имён, мешка слов
    хватает, чтобы отделить «СКА» от «Спартака». PyTorch на сотнях материалов
    и редких кликах запомнит нескольких активных пользователей и хуже
    объясняется.

    fit() — офлайн. rank() только оценивает уже загруженных кандидатов.
    Оба метода не реализованы.

    Колонки articles: news_id, title, body, sport_id, published_at.
    Колонки interactions: user_id, news_id, event_type, created_at.
    event_type: view или comment.

    Оценка качества — разбиение по времени и Recall@K. Accuracy хвалит модель,
    которая всегда отдаёт самый популярный вид спорта. Признак должен быть
    известен в момент рекомендации: будущий счётчик просмотров этого материала
    — утечка. Уже открытые материалы из списка убираются.
    """

    def fit(self, articles, interactions) -> None:
        """Офлайн-шаг.

        articles и interactions — таблицы pandas с колонками из описания класса.
        Здесь учится sklearn TfidfVectorizer. Смесь оценок считает numpy.
        Эти пакеты появятся в зависимостях вместе с первой реализацией fit.
        """

        raise NotImplementedError("NewsRanker.fit")

    def rank(self, user_id: str, candidates) -> list:
        raise NotImplementedError("NewsRanker.rank")
