# Глава 3: Первый пайплайн

> **Запомни:** Пайплайн — это YAML-файл который говорит GitHub: "когда происходит X — сделай Y". Начнём с простого и будем наращивать.

---

## 3.1 Как работает GitHub Actions

```
Событие (push) → Workflow → Job → Step → Action
```

| Уровень | Что это | Аналогия |
|---------|---------|----------|
| **Workflow** | `.github/workflows/ci.yml` | Рецепт |
| **Event** | push, pull_request | Когда готовить |
| **Job** | test, build, deploy | Блюда |
| **Step** | отдельная команда | Ингредиенты |
| **Action** | готовый шаг из маркетплейса | Полуфабрикат |

### Визуально

```
.github/workflows/ci.yml
    │
    ├── on: push              ← КОГДА
    │
    └── jobs:                 ← ЧТО
        ├── test:             ← Job 1
        │   ├── Step 1: checkout
        │   ├── Step 2: setup python
        │   └── Step 3: run pytest
        │
        └── build:            ← Job 2
            ├── Step 1: checkout
            └── Step 2: docker build
```

---

## 3.2 Файл workflow

Создай `.github/workflows/ci.yml`:

```bash
mkdir -p .github/workflows
nano .github/workflows/ci.yml
```

### Минимальный workflow

```yaml
on: [push]

jobs:
  hello:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hello from GitHub Actions!"
      - run: python --version
```

### Разбор каждой строки

```yaml
on: [push]
```
**КОГДА:** при каждом push в любую ветку.

```yaml
jobs:
```
Список задач. Выполняются **параллельно** (если нет `needs:`).

```yaml
  hello:
```
Имя job. Любое уникальное.

```yaml
    runs-on: ubuntu-latest
```
**ГДЕ:** виртуальная машина с Ubuntu.

```yaml
    steps:
```
Список шагов внутри job. Выполняются **последовательно**.

```yaml
      - run: echo "Hello from GitHub Actions!"
```
Выполнить команду в терминале.

### Результат

Push → GitHub Actions запускает → видишь в интерфейсе:

```
✅ hello (Ubuntu)
   ✅ Run echo "Hello from GitHub Actions!"
      Hello from GitHub Actions!
   ✅ Run python --version
      Python 3.12.3
```

---

## 3.3 actions/checkout — забрать код

`run: echo` работает без кода. Но для тестов нужен код из репозитория.

```yaml
on: [push]

jobs:
  hello:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4    ← забирает код
      - run: ls -la                  ← теперь файлы есть
      - run: cat main.py
```

`actions/checkout@v4` — готовое действие из маркетплейса.
Оно делает `git clone` твоего репозитория на Runner.

> **Запомни:** Почти всегда первым шагом идёт `actions/checkout@v4`.
> Без него на Runner нет твоего кода.

---

## 3.4 actions/setup-python — настроить Python

Runner имеет Python но может быть не тот версии.

```yaml
on: [push]

jobs:
  hello:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python --version
      - run: python -c "print('Hello!')"
```

| Часть | Значение |
|-------|----------|
| `uses: actions/setup-python@v5` | Готовое действие |
| `with:` | Параметры действия |
| `python-version: '3.12'` | Какую версию поставить |

---

## 3.5 Несколько jobs

```yaml
on: [push]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Linting..."

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Testing..."

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Building..."
```

**Параллельно:** lint, test, build запускаются одновременно.

### Последовательно

```yaml
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Testing..."

  build:
    needs: test          ← ждёт пока test закончит
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Building..."

  deploy:
    needs: build         ← ждёт пока build закончит
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

```
test → build → deploy
```

> **Запомни:** Без `needs:` jobs параллельны.
> С `needs:` — последовательны.
> Если job упал — следующие не запускаются.

---

## 3.6 Runner: где выполняется

Runner — виртуальная машина GitHub.

| Runner | CPU | RAM | Диск | Бесплатно |
|--------|-----|-----|------|-----------|
| `ubuntu-latest` | 2-core | 7 GB | 14 GB | ✅ 2000 мин/мес |
| `windows-latest` | 2-core | 7 GB | 14 GB | ✅ 2000 мин/мес |
| `macos-latest` | 3-core | 14 GB | 14 GB | ✅ 500 мин/мес |

Для публичных репозиториев — бесплатно без лимита.
Для приватных — 2000 минут в месяц.

---

## 3.7 Как читать логи

После push:

1. GitHub → Actions → кликни на workflow
2. Кликни на job → видишь шаги
3. Кликни на шаг → видишь вывод

### Успешный вывод

```
Run actions/checkout@v4
Syncing repository: user/myapp
  Getting Git version info
  ...
  Checked out repository at abc1234

Run echo "Hello from GitHub Actions!"
  echo "Hello from GitHub Actions!"
  Hello from GitHub Actions!
```

### Провальный вывод

```
Run pytest tests/
  pytest tests/
  ===================== test session starts =====================
  tests/test_main.py::test_home FAILED                    [100%]
  
  ____________________ test_home ____________________
  E   AssertionError: expected 200, got 404
  
  FAILED tests/test_main.py::test_home - AssertionError
  ===================== 1 failed in 0.5s =====================
  Error: Process completed with exit code 1.
```

> **Совет:** Читай снизу вверх. Последняя строка = что сломалось.
> `Error: Process completed with exit code 1` = команда вернула ошибку.

---

## 3.8 Триггеры: когда запускать

### Push в любую ветку

```yaml
on: [push]
```

### Push в конкретную ветку

```yaml
on:
  push:
    branches: [main]
```

### Push и Pull Request

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

### По тегу

```yaml
on:
  push:
    tags:
      - 'v*'
```

### По расписанию (cron)

```yaml
on:
  schedule:
    - cron: '0 6 * * 1'  # Каждый понедельник в 6:00 UTC
```

### Вручную (кнопка)

```yaml
on:
  workflow_dispatch:     # Кнопка "Run workflow" в UI
```

### Комбинация

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:     # можно запустить вручную
```

---

## 3.9 Бейдж статуса в README

Добавь в `README.md`:

```markdown
[![CI](https://github.com/user/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/user/repo/actions/workflows/ci.yml)
```

Результат в README:

```
[![CI](https://img.shields.io/github/actions/workflow/status/user/repo/ci.yml?label=CI)](...)
```

Зелёный бейдж = всё ок. Красный = сломано.

---

## 📝 Упражнения

### Упражнение 3.1: Первый workflow
**Задача:**
1. Создай `.github/workflows/hello.yml`:
   ```yaml
   on: [push]
   jobs:
     hello:
       runs-on: ubuntu-latest
       steps:
         - run: echo "Hello CI/CD!"
   ```
2. Закоммить и запушь
3. Открой GitHub → Actions → увидишь прогон
4. Кликни на job → посмотри логи

### Упражнение 3.2: Сломать и починить
**Задача:**
1. Сделай шаг который упадёт:
   ```yaml
   steps:
     - run: python -c "exit(1)"
   ```
2. Запушь — job упал?
3. Посмотри логи — где ошибка?
4. Почини: `python -c "exit(0)"`

### Упражнение 3.3: Несколько jobs
**Задача:**
1. Создай workflow с двумя jobs:
   ```yaml
   jobs:
     job1:
       runs-on: ubuntu-latest
       steps:
         - run: echo "Job 1"
     job2:
       runs-on: ubuntu-latest
       steps:
         - run: echo "Job 2"
   ```
2. Запустились параллельно? (проверь время в UI)
3. Добавь `needs: job1` в job2 — стали последовательными?

### Упражнение 3.4: Триггеры
**Задача:**
1. Создай workflow который запускается только на `main`:
   ```yaml
   on:
     push:
       branches: [main]
   ```
2. Запушь в feature-ветку — запустился? (не должен)
3. Смерджи в main — запустился?

### Упражнение 3.5: DevOps Think
**Задача:** «Ты запушил код. CI провалился. Но ты уверен что код работает локально. Что проверяешь?»

Подсказки:
1. Какая версия Python на Runner? (`python --version` в шаге)
2. Все ли зависимости установлены? (`pip install -r requirements.txt`)
3. Есть ли файлы которые не закоммичены? (`.gitignore`)
4. Какие именно тесты упали? (смотри логи)

---

## 📋 Чеклист главы 3

- [ ] Я понимаю структуру: workflow → job → step → action
- [ ] Я могу создать `.github/workflows/ci.yml`
- [ ] Я знаю что `actions/checkout@v4` забирает код
- [ ] Я знаю что `actions/setup-python@v5` настраивает Python
- [ ] Я понимаю разницу между `uses:` и `run:`
- [ ] Я понимаю что jobs без `needs:` параллельны
- [ ] Я могу читать логи GitHub Actions
- [ ] Я знаю разные триггеры (push, PR, tag, schedule, manual)
- [ ] Я могу добавить бейдж статуса в README

**Всё отметил?** Переходи к Главе 4 — тесты в пайплайне.
