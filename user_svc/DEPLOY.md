# Запуск user_svc локально

Сервис работает вместе с Keycloak, Postgres и Vault. Секреты Keycloak хранятся в Vault, письма (подтверждение email, сброс пароля) Keycloak отправляет через Google SMTP.

Все команды выполняются из каталога `user_svc`.

## Быстрый старт через скрипт

Скрипт `deploy/stack.sh` выполняет все шаги ниже сам:

```bash
./deploy/stack.sh up          # среда test
./deploy/stack.sh up prod     # среда prod
./deploy/stack.sh status      # контейнеры и состояние Vault
./deploy/stack.sh down        # остановка, данные сохраняются
./deploy/stack.sh reset       # удалить всё (с подтверждением)
```

Что делает `up`:
1. Проверяет Docker и доступность `smtp.gmail.com:587` (если Gmail не отвечает, предупреждает про VPN и продолжает).
2. Если Vault ещё не настроен, запускает bootstrap, где вы придумываете пароль `operator`.
3. Если секрета `google-smtp` для выбранной среды нет, спрашивает адрес Google-аккаунта, пароль приложения (ввод скрыт) и пароль `operator`. Пустой адрес пропускает шаг, секрет можно добавить позже.
4. Собирает и запускает стек, ждёт готовности API и печатает адреса.

Повторный `up` безопасен: ничего не пересоздаётся и не спрашивается, если всё уже настроено. Если вы запускаете другую среду, а база Keycloak создана для прежней, скрипт объясняет причину и предлагает удалить базу Keycloak (данные Vault остаются).

Разделы ниже описывают те же шаги вручную, это справочник.

## Что понадобится

- Docker с Compose.
- Выключенный VPN: Gmail отклоняет SMTP-соединения с адресов многих VPN.
- Google-аккаунт для отправки писем и его пароль приложения (см. ниже).

## Адреса

| Что | Адрес |
|---|---|
| API (Swagger) | `http://localhost:8000/docs` |
| Keycloak | `http://localhost:8080` (для `test`: `admin` / `admin`, realm `sport-pari`) |
| Vault UI | `http://127.0.0.1:8200` |

## Первый запуск

### 1. Поднять Vault и выполнить bootstrap

```bash
docker compose -f deploy/docker-compose.yml up -d vault
docker compose -f deploy/docker-compose.yml --profile bootstrap run --rm vault-bootstrap
```

Скрипт дважды спросит пароль пользователя `operator`. Этот пароль вы придумываете сами: введённое значение и станет паролем. Ввод на экране не отображается. Скрипт нигде его не сохраняет и не показывает, поэтому сразу запишите его в менеджер паролей.

Что делает bootstrap: инициализирует Vault, записывает unseal-ключ и данные AppRole в `deploy/vault/state/` (каталог в `.gitignore`), создаёт секреты Keycloak для сред `test` и `prod`, политики и пользователя `operator`. Root-токен не печатается и в конце отзывается.

Повторный запуск bootstrap безопасен: уже существующее не перезаписывается.

### 2. Создать пароль приложения Google

Пароль приложения нужен потому, что обычный пароль Google-аккаунта для SMTP не подходит.

1. Откройте аккаунт Google, который будет отправителем, затем раздел «Безопасность».
2. Включите двухэтапную аутентификацию (без неё паролей приложений нет).
3. Откройте `https://myaccount.google.com/apppasswords`.
4. Введите название (например, `sport_pari`) и создайте пароль.
5. Скопируйте 16 символов (пробелы лучше убрать). Повторно Google его не показывает.

В аккаунте Google Workspace администратор может запретить пароли приложений, тогда используйте личный `@gmail.com`.

### 3. Положить Google-секрет в Vault

Секрет создаётся вручную, при bootstrap он намеренно пустой.

Через UI: откройте `http://127.0.0.1:8200`, войдите методом **Username** (`operator` и ваш пароль), затем `secret` → Create secret. Путь `test/google-smtp` (для `prod`: `prod/google-smtp`), ключи:

| Ключ | Значение |
|---|---|
| `smtp_user` | адрес Google-аккаунта |
| `smtp_password` | пароль приложения |

Через CLI (пароль `operator` спросят интерактивно):

```bash
docker compose -f deploy/docker-compose.yml run --rm --entrypoint sh vault-init
vault login -method=userpass username=operator
vault kv put secret/test/google-smtp smtp_user=you@gmail.com smtp_password=your-app-password
exit
```

Этот шаг можно выполнить и после запуска стека: сервис `keycloak-sync` применит секрет в Keycloak в течение 30 секунд, перезапуск не нужен. Письма уходят с адреса `smtp_user`.

### 4. Запустить стек

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

Первый запуск скачивает образы и занимает около минуты. По умолчанию используется среда `test`. Для `prod`:

```bash
APP_ENV=prod docker compose -f deploy/docker-compose.yml up -d --build
```

Переменную `APP_ENV` передавайте именно так или через `--env-file .env`: Compose сам читает `.env` рядом с compose-файлом (в `deploy/`), а не в корне `user_svc`.

Проверка состояния:

```bash
docker compose -f deploy/docker-compose.yml ps -a
```

`vault-init` в состоянии `Exited (0)`, это нормально: он одноразовый.

## Как проверить, что всё работает

```bash
curl -s -X POST localhost:8000/registration -H 'content-type: application/json' \
  -d '{"username":"alice","email":"you@gmail.com","password":"Password-12345"}'
```

В ответе должно быть `"verification_sent": true`, на почту придёт письмо. Ссылка в нём ведёт на `localhost:8080`: откройте её в браузере и нажмите «Click here to proceed».

Пока аккаунт не подтверждён, `/login` возвращает 403 `email not verified`; после подтверждения возвращает токен:

```bash
curl -s -X POST localhost:8000/login -H 'content-type: application/json' \
  -d '{"username":"alice","password":"Password-12345"}'
```

Если `verification_sent` равен `false`, письмо не ушло. Регистрация при этом состоялась, и письмо можно запросить повторно через `POST /send-verify` с телом `{"email": "..."}`. Причину смотрите в логах:

```bash
docker compose -f deploy/docker-compose.yml logs keycloak keycloak-sync
```

## Какие секреты можно менять без перезапуска

Меняются в Vault (UI или CLI под `operator`), `keycloak-sync` применяет их в течение 30 секунд.

| Секрет | Без перезапуска |
|---|---|
| `google-smtp`: `smtp_user`, `smtp_password` | да |
| `keycloak`: `admin_password` | да |
| `keycloak`: `admin_username` | нет |
| `keycloak`: `db_password` | нет: нужен `ALTER USER` в Postgres и перезапуск Keycloak |
| `keycloak`: `client_secret` | нет: нужен перезапуск `api` и ручное обновление секрета клиента в Keycloak |

Если админский пароль в Vault и в Keycloak разошлись и ни одна версия секрета не подходит, `keycloak-sync` пишет ошибку в лог (один раз на версию) и ничего не меняет.

## Остановка и повторный запуск

- `docker compose -f deploy/docker-compose.yml down`: данные Vault и пользователи Keycloak сохраняются. Следующий `up -d` сам распечатывает Vault (делает unseal ключом из `deploy/vault/state/unseal.key`).
- `docker compose -f deploy/docker-compose.yml down -v`: удаляет всё. После этого удалите `deploy/vault/state/unseal.key` и `deploy/vault/state/approle` и снова пройдите bootstrap.
- Переключение между `test` и `prod`: пароль БД Keycloak задаётся один раз при создании Postgres, поэтому перед запуском другой среды остановите стек и удалите базу Keycloak: `docker volume rm user-svc_keycloak-db`. Данные Vault сохраняются.

## Запуск API вне Docker

Возможен, но Keycloak, Postgres и Vault всё равно запускаются в Docker (остановите только контейнер `api`). Приложение не читает `.env` само: выставьте переменные вручную.

```bash
set -a; . ./.env; set +a
uv run uvicorn app.main:app --port 8000
```

В `.env` должны быть `KEYCLOAK_URL=http://localhost:8080`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` и `KEYCLOAK_CLIENT_SECRET` (для `test`: `dev-secret-change-me`). Пример значений в `.env.example`.

## Если что-то не работает

| Симптом | Что проверить |
|---|---|
| `vault-init` завершился с ошибкой «run vault-bootstrap first» | не выполнен шаг 1 или удалены файлы в `deploy/vault/state/` |
| Письма не уходят, в логе Keycloak `Got bad greeting from SMTP host` | выключите VPN, проверьте `openssl s_client -starttls smtp -connect smtp.gmail.com:587 -crlf` (должна быть строка `250 ...`) |
| Письма не уходят, ошибка аутентификации Gmail | в `smtp_password` должен быть пароль приложения, а не обычный пароль аккаунта |
| Keycloak и `api` не стартуют после смены среды | удалите `user-svc_keycloak-db` (см. выше) |
| `keycloak-sync` пишет `vault is sealed` | Vault запечатан: выполните `docker compose -f deploy/docker-compose.yml up -d` |
| Забыт пароль `operator` | bootstrap его не сбрасывает. В dev проще всего `down -v`, удалить `deploy/vault/state/unseal.key` и `deploy/vault/state/approle` и пройти bootstrap заново (данные Vault и Keycloak будут потеряны). Чтобы сохранить данные, выпустите временный root-токен по unseal-ключу (`vault operator generate-root`, см. документацию Vault) и задайте новый пароль командой `vault write auth/userpass/users/operator password=...`; эта процедура не автоматизирована и не проверялась |

## Ограничения

Этот стек подходит для разработки и тестирования, не для боевого сервера:

- Keycloak запущен в режиме `start-dev` (без HTTPS и настроенного hostname, порт 8080 открыт).
- Unseal-ключ лежит на диске хоста в `deploy/vault/state/`, рядом с остальными данными стека, но вне volume Vault.
- Файл `runtime.env` с секретами лежит в docker volume на диске хоста, значения видны в `docker inspect`.
- Трафик до Vault внутри docker-сети идёт без TLS, порт Vault доступен только на `127.0.0.1`.
