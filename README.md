# sport_pari

Общая ветка `main` — точка слияния сервисных веток. Каждый работает в своей ветке и вливает её в `main`.

## Архитектура

Клиент ходит в API Gateway по HTTPS. Gateway разводит запросы по четырём сервисам. Сервисы публикуют события в Kafka и используют общий Redis для кэша и pub/sub. Метрики и трейсы собирают Prometheus, Grafana и OpenTelemetry.

Шлюз на схеме — **nginx / Traefik**. Допустимый вариант края: **FastAPI + httpx** как reverse-proxy, либо **Traefik** как edge.

```mermaid
flowchart TB
    FE["Frontend (Next.js)"]
    FE -->|HTTPS| GW["API Gateway<br/>nginx / Traefik"]

    GW --> US["User Service<br/>FastAPI<br/>PostgreSQL · Redis"]
    GW --> NS["News Svc<br/>FastAPI<br/>Postgres · ES · MinIO"]
    GW --> SS["Sports Svc<br/>FastAPI<br/>Postgres · Redis · WS"]
    GW --> PN["Prediction / Notify<br/>FastAPI + workers<br/>Postgres · Redis<br/>Celery / ARQ"]

    US --> K["Kafka<br/>events"]
    NS --> K
    SS --> K
    PN --> K

    US --> R["Redis<br/>cache, pub/sub"]
    NS --> R
    SS --> R
    PN --> R

    K --> OBS[" "]
    R --> OBS
    OBS --> PROM["Prometheus"]
    OBS --> GRAF["Grafana"]
    OBS --> OTEL["OpenTelemetry"]

    style OBS fill:none,stroke:none
```

## Сервисы

| Сервис | Стек |
| --- | --- |
| User Service | FastAPI, PostgreSQL, Redis |
| News Svc | FastAPI, Postgres, Elasticsearch, MinIO |
| Sports Svc | FastAPI, Postgres, Redis, WebSocket |
| Prediction / Notify | FastAPI и воркеры, Postgres, Redis, Celery или ARQ |

Общая инфраструктура: Kafka (события), Redis (кэш и pub/sub), Prometheus, Grafana, OpenTelemetry.
