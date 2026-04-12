# Глава 4: Тесты в пайплайне

> **Запомни:** CI без тестов — просто "запустить скрипт при push". Ценность CI именно в том что он говорит "этот коммит сломал вот это".

---

## 4.1 Зачем тесты в CI

Локально ты запускаешь тесты перед коммитом. Но:

- **Забыл** запустить → баг в main
- **Пропустил** один тест → "я думал остальные прошли"
- **У тебя работает** но не работает на другой версии Python

**CI гарантирует:** каждый коммит проверяется. Без забывчивости. Без "у меня работает".

```
Push → CI запускает тесты → ✅ прошло → merge разрешён
                            → ❌ упало  → merge заблокирован
```

---

## 4.2 Установка зависимостей и запуск pytest

### Минимальный workflow с тестами

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --tb=short
```

### Разбор новых элементов

```yaml
      - name: Install dependencies
```
**name** = подпись шага в логах. Без него — видна команда.

```
✅ Install dependencies
   pip install -r requirements.txt
   Collecting flask...
```

Без `name:`:

```
✅ Run pip install -r requirements.txt
   Collecting flask...
```

> **Совет:** Используй `name:` когда команда длинная.
> Легче читать логи.

```yaml
      - name: Run tests
        run: pytest --tb=short
```

`--tb=short` = короткий traceback. Меньше мусора в логах.

### requirements.txt для тестов

```
flask
pytest
pytest-cov
```

CI установит то же что и у тебя локально.

---

## 4.3 actions/setup-python — зачем action а не просто python

Runner уже имеет Python. Зачем `setup-python`?

```yaml
# Без setup-python
- run: python --version
  # Python 3.10.12 (системный на Ubuntu Runner)

# С setup-python
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
- run: python --version
  # Python 3.12.3 (точно нужная версия)
```

**Зачем:**
- Точная версия Python (не зависит от Runner)
- Кэш pip (ускоряет установку зависимостей)
- Предсказуемость

---

## 4.4 Матрица версий Python

Тестируй на нескольких версиях одновременно:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --tb=short
```

### Что происходит

```
Push → test (3.11) → ✅
     → test (3.12) → ✅
```

Два job запускаются **параллельно** на разных версиях Python.

### В интерфейсе GitHub

```
All checks (2)
  ✅ test (3.11)
  ✅ test (3.12)
```

Если одна версия упала:

```
All checks (2)
  ✅ test (3.11)
  ❌ test (3.12) — 1 failed
```

Merge заблокирован.

> **Запомни:** Матрица = параллельные job для каждой комбинации.
> Можно добавить ещё ОС, версии БД и т.д.

---

## 4.5 Кэш зависимостей: `actions/cache`

Без кэша каждый запуск — установка всех пакетов заново.

```
pip install -r requirements.txt
  Collecting flask...     ← 30 секунд каждый раз
```

С кэшем:

```
pip install -r requirements.txt
  Using cached flask...   ← 3 секунды
```

### Настройка кэша pip

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'          ← кэш pip включён!

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest --tb=short
```

`cache: 'pip'` — setup-python сам настроит кэш.

> **Совет:** Всегда включай `cache: 'pip'` в setup-python.
> Экономит 20-60 секунд на каждом прогоне.

---

## 4.6 Блокировка merge при упавших тестах

### Protection rules

GitHub → Settings → Branches → Add rule → main:

```
✅ Require a pull request before merging
✅ Require status checks to pass before merging
   Status checks that are required:
     ☑ test (3.11)
     ☑ test (3.12)
✅ Require branches to be up to date before merging
```

### Что происходит

```
PR #5: Add new feature
  ❌ test (3.12) — 1 failed

[Merge Pull Request] ← ЗАБЛОКИРОВАНА (серая)
```

После исправления:

```
PR #5: Add new feature
  ✅ test (3.11)
  ✅ test (3.12)

[Merge Pull Request] ← РАЗБЛОКИРОВАНА (зелёная)
```

> **Запомни:** Имя status check = имя job в workflow.
> Если job называется `test` — ищи "test" в списке.
> Если с матрицей — `test (3.11)`, `test (3.12)`.

---

## 4.7 Покрытие кода: pytest-cov

### Установка

```
# requirements.txt
pytest-cov
```

### Запуск

```yaml
      - name: Run tests with coverage
        run: pytest --cov=. --cov-report=term-missing
```

### Вывод в логах

```
Name          Stmts   Miss  Cover   Missing
-------------------------------------------
main.py          45      3    93%   12-14
tests/test.py    30      0   100%
-------------------------------------------
TOTAL            75      3    96%
```

---

## 📝 Упражнения

### Упражнение 4.1: Тесты в CI
**Задача:**
1. Создай `tests/test_main.py`:
   ```python
   def test_home():
       assert 1 + 1 == 2
   ```
2. Создай workflow с тестами (как в 4.2)
3. Запушь — тесты прошли?
4. Сделай тест который падает: `assert 1 + 1 == 3`
5. Запушь — тест упал в CI?

### Упражнение 4.2: Матрица версий
**Задача:**
1. Добавь матрицу Python 3.11 и 3.12
2. Запушь — два job запустились параллельно?
3. Сделай код который работает только на 3.12 (f-string с =)
4. На 3.11 упал? На 3.12 прошёл?

### Упражнение 4.3: Кэш
**Задача:**
1. Запусти workflow без кэша — посмотри сколько заняла установка
2. Добавь `cache: 'pip'`
3. Запусти снова — стало быстрее?

### Упражнение 4.4: Блокировка PR
**Задача:**
1. Настрой branch protection для main
2. Require status check: "test"
3. Создай PR с упавшим тестом — merge заблокирован?
4. Почини тест — merge разблокирован?

### Упражнение 4.5: DevOps Think
**Задача:** «CI показывает что тесты проходят но код на сервере не работает. Почему?»

Подсказки:
1. Тесты проверяют только то что ты написал
2. Есть ли интеграционные тесты (с реальной БД)?
3. Тесты на Runner vs тесты локально — одинаковые ли зависимости?
4. Может проблема не в коде а в конфиге сервера?

---

## 📋 Чеклист главы 4

- [ ] Я понимаю зачем тесты в CI (не "проверить" а "гарантировать")
- [ ] Я могу настроить pytest в workflow
- [ ] Я понимаю зачем `actions/setup-python` (не системный Python)
- [ ] Я могу настроить матрицу версий Python
- [ ] Я могу включить кэш pip (`cache: 'pip'`)
- [ ] Я понимаю как блокировать merge при упавших тестах
- [ ] Я могу запустить тесты с покрытием (`--cov`)
- [ ] Я знаю что имя status check = имя job в workflow

**Всё отметил?** Переходи к Главе 5 — секреты и переменные.
