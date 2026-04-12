# Приложение A: Шпаргалка по GitHub Actions

---

## Контексты

### `github.*`

| Переменная | Значение |
|-----------|----------|
| `github.sha` | Хэш коммита |
| `github.ref_name` | Имя ветки или тега |
| `github.actor` | Кто запустил |
| `github.event_name` | Тип события (push, pull_request) |
| `github.repository` | user/repo |
| `github.workflow` | Имя workflow |
| `github.job` | Имя текущего job |
| `github.run_id` | ID запуска |
| `github.workspace` | Путь к коду на Runner |

### `secrets.*`

```yaml
${{ secrets.SERVER_HOST }}
${{ secrets.SSH_PRIVATE_KEY }}
${{ secrets.GITHUB_TOKEN }}    ← автоматический
```

### `env.*`

```yaml
# В workflow
env:
  MY_VAR: hello

# В шаге
${{ env.MY_VAR }}

# В run
$MY_VAR
```

---

## Часто используемые Actions

| Action | Что делает |
|--------|-----------|
| `actions/checkout@v4` | Забрать код из репозитория |
| `actions/setup-python@v5` | Установить Python |
| `actions/cache@v4` | Кэш файлов |
| `actions/upload-artifact@v4` | Сохранить артефакт |
| `actions/download-artifact@v4` | Скачать артефакт |
| `docker/login-action@v3` | Логин в Docker registry |
| `docker/build-push-action@v5` | Сборка и push Docker образа |
| `docker/metadata-action@v5` | Автоматические теги |
| `appleboy/ssh-action@v1` | SSH команды на сервер |

---

## Триггеры

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:        # кнопка в UI
  schedule:
    - cron: '0 6 * * 1'   # cron UTC
  push:
    tags:
      - 'v*'
```

---

## Структура workflow

```yaml
name: My Workflow          # имя
on: [push]                 # триггеры

jobs:                      # задачи
  job-name:                # имя job
    runs-on: ubuntu-latest # где
    needs: other-job       # зависимости
    if: github.ref == 'refs/heads/main'  # условие
    strategy:
      matrix:              # матрица
        version: ['3.11', '3.12']
    steps:                 # шаги
      - uses: actions/checkout@v4    # готовый action
      - run: echo "hello"            # команда
      - name: My Step                # имя шага
        run: echo "hello"
        env:                         # переменные шага
          MY_VAR: value
```

---

## Команды для отладки

```yaml
steps:
  - run: echo "SHA=${{ github.sha }}"
  - run: echo "Branch=${{ github.ref_name }}"
  - run: env                     # все переменные
  - run: ls -la                  # файлы
  - run: python --version        # версия Python
  - run: cat requirements.txt    # зависимости
```
