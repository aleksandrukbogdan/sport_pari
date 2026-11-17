# sport_pari frontend

Общий интерфейс. Живые запросы идут в user, news, sports и prediction. Режим `DATA_MODE=demo` показывает учебные карточки и не вызывает серверы.

## Запуск всего приложения

Из корня репозитория:

```powershell
docker compose up -d vault
docker compose --profile bootstrap run --rm vault-bootstrap
docker compose up --build
```

Первый `vault-bootstrap` один раз спрашивает пароль `operator` и записывает ключи в `user_svc/deploy/vault/state`. Почту Google можно не вводить. Повторный `docker compose up` пароль не спрашивает.

Адреса:

- интерфейс: http://localhost:3000
- пользователи: http://localhost:8001/docs
- новости: http://localhost:8002/docs
- матчи: http://localhost:8003/docs
- прогнозы: http://localhost:8004/docs
- Keycloak: http://localhost:18080
- Vault: http://127.0.0.1:8200

Администратор прогнозов — пользователь, чей `sub` или `preferred_username` входит в `ADMIN_USER_IDS` (по умолчанию `admin`).

## Проверка

1. Зарегистрируйтесь и войдите на http://localhost:3000. Откройте профиль.
2. Лента новостей на порту 8002 и комментарий от вошедшего пользователя.
3. `GET http://localhost:8003/events` содержит `match.scheduled` для матча 3. Те же команды видны в разделе «Матчи и статистика».
4. После старта consumer копия матча 3 есть в прогнозах. Администратор создаёт вопрос и отправляет ответ «да» или «нет».

## Чего на серверах нет

- Кабинет преподавателя, учебные группы и оценка аргументации.
- Сохранение обоснования прогноза.
- Связь новости с матчем: у новости нет идентификатора матча.
- Каталог команд. Интересы хранят введённые строки.
- Скрытие комментария в интерфейсе: отдельного метода для зрителя нет.
- Оценка верности ответа «да/нет». `factual_outcome` — это итог матча.
- `match.updated` и WebSocket у Sports.
