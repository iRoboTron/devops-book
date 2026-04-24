# Глава 6: Сборка и публикация Docker-образа

> **Запомни:** Сервер не должен собирать образ. Он должен тянуть готовый. CI собирает → публикует → сервер скачивает и запускает.

---

## 6.1 Зачем реестр образов

### Без реестра (плохо)

```
CI: собирает образ на Runner
         ↓
    ??? как доставить на сервер
         ↓
Сервер: собирает образ сам  ← долго, непредсказуемо
```

### С реестром (хорошо)

```
CI: собирает образ → публикует в ghcr.io
                             ↓
Сервер: docker pull ghcr.io/...  ← быстро, одинаково
```

> **Запомни:** Реестр = CDN для Docker-образов.
> Собран один раз — работает одинаково везде.

---

## 6.2 GitHub Container Registry (ghcr.io)

**ghcr.io** — реестр образов от GitHub. Бесплатно, встроено.

```
ghcr.io/adelfos/myapp:abc123
└──┬──┘ └───┬───┘ └─┬──┘ └──┬──┘
реестр  пользователь  имя   тег (commit SHA)
```

---

## 6.3 Логин в ghcr.io из Actions

```yaml
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

### `GITHUB_TOKEN` — что это

Автоматический токен который GitHub создаёт для каждого запуска workflow.

| Свойство | Значение |
|----------|----------|
| Создаётся | Автоматически |
| Живёт | Один запуск workflow |
| Права | Чтение/запись твоего репозитория |
| Нужно создавать | Нет |

> **Запомни:** Для ghcr.io не нужно создавать отдельный токен.
> `GITHUB_TOKEN` работает из коробки.
> Просто используй `${{ secrets.GITHUB_TOKEN }}`.

---

## 6.4 Сборка и публикация

### docker/build-push-action

```yaml
- uses: docker/build-push-action@v5
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

| Параметр | Значение |
|----------|----------|
| `push: true` | Опубликовать после сборки |
| `tags:` | Как назвать образ |

### Полный job сборки

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 6.5 Тегирование образов

### По SHA коммита

```yaml
tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

```
ghcr.io/adelfos/myapp:abc123def456
```

**Плюсы:** Каждый коммит = уникальный образ. Легко откатиться.
**Минусы:** Неудобно запоминать.

### По ветке

```yaml
tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

```
ghcr.io/adelfos/myapp:main
ghcr.io/adelfos/myapp:feature/login
```

### По тегу git

```yaml
# Только при push тега
on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    steps:
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

```
ghcr.io/adelfos/myapp:v1.0.0
```

### Несколько тегов

```yaml
tags: |
  ghcr.io/${{ github.repository }}:${{ github.sha }}
  ghcr.io/${{ github.repository }}:latest
```

Один образ — два имени.

> **Запомни:** Для деплоя используй SHA.
> Для удобства — ещё и `latest` или имя ветки.

---

## 6.6 Кэш слоёв Docker

Без кэша — сборка с нуля каждый раз.

```
Step 1/8: FROM python:3.12-slim          ← 30 сек
Step 2/8: WORKDIR /app                   ← 1 сек
Step 3/8: COPY requirements.txt .        ← 1 сек
Step 4/8: RUN pip install ...            ← 60 сек ← каждый раз!
Step 5/8: COPY . .                       ← 1 сек
```

С кэшем:

```
Step 4/8: RUN pip install ...            ← CACHED! 0 сек
```

### Настройка кэша

```yaml
- uses: docker/build-push-action@v5
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
    cache-from: type=gha        ← читать кэш GitHub Actions
    cache-to: type=gha,mode=max ← записывать кэш
```

`type=gha` = использовать Actions Cache.

> **Совет:** Всегда добавляй `cache-from` и `cache-to`.
> Экономит минуты сборки.

---

## 6.7 docker/metadata-action — автоматические теги

Вместо ручного тегирования:

```yaml
- name: Extract metadata
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: ghcr.io/${{ github.repository }}

- uses: docker/build-push-action@v5
  with:
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
```

Автоматически создаёт теги:

| Событие | Теги |
|---------|------|
| Push в main | `main`, `sha-abc123` |
| Push тега `v1.0.0` | `1.0.0`, `1.0`, `1`, `latest` |
| PR #42 | `pr-42` |

---

## 6.8 Проверка что образ опубликован

GitHub → Репозиторий → **Packages** → видишь свой образ:

```
myapp
  v1.0.0    156 MB    2 hours ago
  main      156 MB    5 hours ago
```

Или через CLI:

```bash
docker pull ghcr.io/adelfos/myapp:abc123
```

---

## 📝 Упражнения

### Упражнение 6.1: Сборка и публикация
**Задача:**
1. Создай workflow с job сборки (как в 6.4)
2. Запушь — job выполнился?
3. Проверь GitHub → Packages — образ появился?
4. Попробуй: `docker pull ghcr.io/твой-username/твой-репо:sha`

### Упражнение 6.2: Кэш
**Задача:**
1. Запусти сборку без кэша — посмотри время
2. Добавь `cache-from: type=gha, cache-to: type=gha`
3. Запусти снова — стало быстрее?

### Упражнение 6.3: Метаданные
**Задача:**
1. Добавь docker/metadata-action
2. Запушь — какие теги создал?
3. Создай тег `v0.1.0` и запушь — появились теги `0.1.0`, `0.1`, `0`?

### Упражнение 6.4: DevOps Think
**Задача:** «Образ в ghcr.io не обновляется после push. Старая версия деплоится. Почему?»

Подсказки:
1. `push: true` стоит в build-push-action?
2. Тег правильный? (`github.sha` vs `github.ref_name`)
3. Сервер тянет тот же тег? (`docker-compose.yml` использует правильную переменную)
4. GITHUB_TOKEN есть права на запись Packages?

---

## 📋 Чеклист главы 6

- [ ] Я понимаю зачем реестр образов (сервер не собирает сам)
- [ ] Я могу залогиниться в ghcr.io из Actions
- [ ] Я понимаю что `GITHUB_TOKEN` создаётся автоматически
- [ ] Я могу собрать и опубликовать образ (`docker/build-push-action`)
- [ ] Я понимаю систему тегов (SHA, ветка, git-тег)
- [ ] Я могу настроить кэш слоёв Docker (`cache-from: type=gha`)
- [ ] Я могу использовать `docker/metadata-action` для авто-тегов
- [ ] Я могу проверить что образ опубликован (GitHub → Packages)

**Всё отметил?** Переходи к Главе 7 — автодеплой на сервер.
