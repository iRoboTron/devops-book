# Приложение A: Operability cheatsheet

## Operability score

10 пунктов по 2 балла. Максимум 20.

```text
0–8:  работает у автора
9–14: базовая зрелость
15–20: готово к командной эксплуатации
```

## Stateless vs stateful

| Тип | Можно пересоздать? | Нужен backup? |
|---|---|---|
| app container | да | нет |
| PostgreSQL volume | нет | да |
| uploads | нет | да |
| cache | зависит | обычно нет |
| очередь | зависит | часто нужна защита |

## Healthcheck

| Endpoint | Значение |
|---|---|
| `/healthz` | процесс жив |
| `/readyz` | сервис готов принимать трафик |
| `/metrics` | метрики для мониторинга |

## Graceful shutdown

```text
SIGTERM -> stop accepting -> finish requests -> close connections -> exit
```

## Миграции

```text
expand -> backfill -> contract
```

Сначала добавить новое, потом перенести данные, потом удалить старое.

## Retry policy

Минимум:

- timeout;
- сколько retry;
- backoff;
- что делать при окончательной ошибке;
- идемпотентна ли операция.

## Structured log

```json
{"level":"error","service":"api","request_id":"abc123","action":"create_order","error":"payment_timeout"}
```

## Стратегии деплоя

| Стратегия | Когда |
|---|---|
| in-place | маленький сервис |
| rolling | stateless + совместимость |
| blue-green | нужен быстрый rollback |
| canary | большой трафик и риск |