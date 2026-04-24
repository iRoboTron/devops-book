# Глава 1: Git — ветки, merge, pull request

> **Запомни:** CI/CD деплоит то что в ветке `main`. Всё что не в `main` — не на сервере. Ветки — это способ работать безопасно, не ломая продакшн.

---

## 1.1 Ветки: зачем они в контексте деплоя

Представь: ты работаешь над новой фичей. Код не готов. Но сервер должен работать стабильно.

**Без веток:**
```
main:  ───●──●──●──●──X──●───  ← X = баг, все пользователи видят
           │        ↑
           │        деплой
           └──── разрабатываешь фичу прямо в main
```

**С ветками:**
```
main:      ───●──●──●────────────●────  ← всегда стабильно
                  ↑               ↑
               деплой          деплой

feature:        ───●──●──●──●───  ← тут ломаешь, чинишь, экспериментируешь
                           ↑
                      merge в main когда готово
```

> **Запомни:** `main` = то что в продакшне.
> Никогда не ломай `main`. Работай в feature-ветках.

---

## 1.2 GitHub Flow — простая стратегия

Есть много стратегий ветвления. Для CI/CD достаточно **GitHub Flow**:

```
main ─────────────────────────────────────── [продакшн]
       ↑ merge          ↑ merge
       │                │
f/login ──────┐     f/api ───────┐
              │                   │
        разработка           разработка
```

**Правила:**
1. `main` всегда стабильна и готова к деплою
2. Новая фича = новая ветка от `main`
3. Ветка называется `feature/название` или `fix/название`
4. Когда готово — Pull Request → merge в `main`
5. `main` автоматически деплоится

### Почему не Git Flow

Git Flow сложнее: `develop`, `release`, `hotfix`, `main`.
Для small/mid проектов — избыточно.

GitHub Flow = достаточно для 90% команд.

---

## 1.3 Работа с ветками

### Создать ветку

```bash
git checkout -b feature/login
```

`-b` = создать и переключиться.

### Посмотреть ветки

```bash
git branch
* feature/login
  main
```

`*` = текущая ветка.

### Переключиться

```bash
git checkout main
git checkout feature/login
```

### Закоммитить

```bash
git add .
git commit -m "Add login form"
git push -u origin feature/login
```

`-u` = установить upstream (чтобы потом просто `git push`).

---

## 1.4 `git merge` vs `git rebase`

### merge

```bash
git checkout main
git merge feature/login
```

```
main:   ───●──●────────────●──  ← merge commit
               ↗          ↗
feature:      ●──●──●──●──
```

Создаёт **merge commit** — точку соединения.

**Плюсы:** Сохраняет полную историю.
**Минусы:** История "грязная" с merge-коммитами.

### rebase

```bash
git checkout feature/login
git rebase main
```

```
main:   ───●──●──●──●──●──  ← линейная история
feature:         ↗
              ●──●──●──●  ← перенесено наверх
```

Переносит твои коммиты **наверх** актуальной `main`.

**Плюсы:** Линейная чистая история.
**Минусы:** Переписывает историю (опасно для общих веток).

### Когда что использовать

| Ситуация | Команда |
|----------|---------|
| Feature-ветка → main | `merge` (через PR) |
| Обновить feature-ветку из main | `rebase` |
| Hotfix → main | `merge` |

> **Правило:** Rebase локальных веток — ok.
> Rebase общих веток (main, develop) — никогда.

---

## 1.5 Pull Request

**Pull Request (PR)** — предложение смержить ветку в `main`.

### Создать PR

```bash
git push -u origin feature/login
# На GitHub: New Pull Request → feature/login → main
```

### Что происходит в PR

```
PR #42: Add login form
├── Файлы которые изменились
├── Diff (что добавлено/удалено)
├── CI检查结果  ← GitHub Actions запустил тесты!
├── Код-ревью от коллеги
└── [Merge Pull Request] кнопка
```

### CI в PR

GitHub Actions автоматически запускает тесты для PR:

```
PR #42: Add login form
├── ✅ All checks passed (3/3)
│   ✅ lint (12s)
│   ✅ test py3.11 (45s)
│   ✅ test py3.12 (38s)
└── [Merge Pull Request] ← разблокирована
```

Если тесты упали:

```
PR #42: Add login form
├── ❌ 2/3 checks failed
│   ✅ lint
│   ❌ test py3.11 — 2 failed
│   ❌ test py3.12 — 2 failed
└── [Merge Pull Request] ← заблокирована
```

> **Запомни:** PR с упавшими тестами = нельзя мержить.
> Это главная ценность CI — не пускать сломанный код в main.

---

## 1.6 Защита ветки main

**Branch protection** — запретить прямой push в `main`.

### Настройка

GitHub → Settings → Branches → Add rule:

```
Branch name pattern: main

✅ Require a pull request before merging
✅ Require status checks to pass before merging
   ✅ test (ищи свой job)
✅ Require conversation resolution before merging
```

### Что это даёт

```bash
git push origin main
# remote: error: GH006: Protected branch update failed.
# remote: error: Direct push to 'main' is not allowed.
```

Теперь **только через PR** → тесты → merge.

> **Запомни:** Защита main — must have для CI/CD.
> Без неё кто-то (или ты) запушит баг напрямую.

---

## 1.7 Теги и версии

**Тег** — метка на конкретном коммите.

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Семантическое версионирование

```
v1.2.3
 ↑ ↑ ↑
 │ │ └── Patch: баг-фикс
 │ └──── Minor: новая фича (обратно совместима)
 └────── Major: ломающее изменение
```

| Изменение | Версия |
|-----------|--------|
| Исправил баг | `1.0.0` → `1.0.1` |
| Добавил API endpoint | `1.0.0` → `1.1.0` |
| Изменил формат ответа API | `1.0.0` → `2.0.0` |

### Теги в CI/CD

Тег может запускать отдельный пайплайн:

```yaml
on:
  push:
    tags:
      - 'v*'
```

Push тега `v1.0.0` → деплой в production.

---

## 1.8 `git log` — видеть историю

```bash
git log --oneline --graph --all
* abc1234 (HEAD -> main) Merge PR #42
|\
| * def5678 (feature/login) Add login form
| * ghi9012 Add login button
* | jkl3456 Fix typo in README
|/
* mno7890 Previous release
```

| Флаг | Что делает |
|------|-----------|
| `--oneline` | Один коммит = одна строка |
| `--graph` | ASCII-граф веток |
| `--all` | Все ветки |
| `--decorate` | Показать теги и ветки |

> **Совет:** Используй `git log --oneline --graph --all` чтобы
> видеть что происходит в репозитории.

---

## 📝 Упражнения

### Упражнение 1.1: Создать ветку
**Задача:**
1. Создай репозиторий на GitHub (или используй существующий)
2. Клонируй: `git clone git@github.com:user/repo.git`
3. Создай ветку: `git checkout -b feature/test`
4. Создай файл: `nano test.txt`, вставь `test`, сохрани: `Ctrl+O`, `Enter`, `Ctrl+X`
5. Закоммить: `git add . && git commit -m "Add test file"`
6. Запушь: `git push -u origin feature/test`

### Упражнение 1.2: Pull Request
**Задача:**
1. На GitHub создай PR: feature/test → main
2. Посмотри diff файлов
3. Смерджи PR
4. Проверь на локальной машине: `git checkout main && git pull`

### Упражнение 1.3: История
**Задача:**
1. Сделай 3-4 коммита в разных ветках
2. Посмотри историю: `git log --oneline --graph --all`
3. Видишь ветвление и merge?

### Упражнение 1.4: Тег
**Задача:**
1. Поставь тег: `git tag v0.1.0`
2. Запушь тег: `git push origin v0.1.0`
3. Проверь на GitHub — тег появился?

### Упражнение 1.5: DevOps Think
**Задача:** «Коллега запушил код напрямую в main без PR. Сервер сломался. Как предотвратить в будущем?»

Ответ:
1. Включить branch protection для main
2. Require PR перед merge
3. Require status checks (тесты) перед merge
4. Запретить force push в main
5. Теперь никто (даже админ) не сможет запушить напрямую

---

## 📋 Чеклист главы 1

- [ ] Я понимаю зачем нужны ветки в контексте деплоя
- [ ] Я знаю GitHub Flow (main + feature-ветки)
- [ ] Я могу создать, переключиться, запушить ветку
- [ ] Я понимаю разницу merge vs rebase
- [ ] Я знаю что такое Pull Request
- [ ] Я понимаю как CI проверяет PR (тесты блокируют merge)
- [ ] Я могу защитить ветку main
- [ ] Я понимаю семантическое версионирование (SemVer)
- [ ] Я могу посмотреть историю (`git log --oneline --graph --all`)

**Всё отметил?** Переходи к Главе 2 — Git Hooks.
