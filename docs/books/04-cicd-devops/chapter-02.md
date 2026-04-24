# Глава 2: Git Hooks — автоматизация на уровне git

> **Запомни:** Git хуки — это скрипты которые запускаются автоматически при определённых действиях git. Хочешь проверить код до коммита? Хук. Хочешь деплоить после push? Хук.

---

## 2.1 Что такое git hook

**Git hook** — скрипт в `.git/hooks/` который git запускает автоматически.

```
git commit → pre-commit hook → если ок → commit
                                      ↓ нет
                                   отмена
```

Это как триггеры в базе данных. Действие → автоматически что-то происходит.

### Где лежат хуки

```
myproject/.git/hooks/
├── pre-commit.sample      ← перед коммитом
├── commit-msg.sample      ← проверка сообщения
├── pre-push.sample        ← перед push
├── post-receive.sample    ← после получения (сервер)
└── ...
```

`.sample` = неактивны. Убери `.sample` или создай свой файл без расширения — git запустит.

---

## 2.2 Хуки на клиенте

### pre-commit — проверить код до коммита

Создай `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Проверяем что нет синтаксических ошибок Python

echo "Running pre-commit checks..."

# Проверка синтаксиса
python -m py_compile $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
if [ $? -ne 0 ]; then
    echo "❌ Python syntax error!"
    exit 1
fi

echo "✅ All checks passed"
exit 0
```

Сделай выполняемым:

```bash
chmod +x .git/hooks/pre-commit
```

Теперь при каждом `git commit`:

```bash
git commit -m "Add feature"
Running pre-commit checks...
✅ All checks passed
[feature/login abc123] Add feature
```

Если ошибка:

```bash
git commit -m "Add feature"
Running pre-commit checks...
  File "main.py", line 10
    def broken(
              ^
SyntaxError: '(' was never closed
❌ Python syntax error!
```

Коммит **отменён**.

> **Запомни:** pre-commit хук не даст закоммитить сломанный код.
> Но он работает только локально, у тебя на машине.

---

### commit-msg — проверить формат сообщения

Создай `.git/hooks/commit-msg`:

```bash
#!/bin/bash
# Проверяем что сообщение коммита не пустое и начинается с заглавной

MSG=$(cat "$1")

if [ -z "$MSG" ]; then
    echo "❌ Сообщение коммита пустое!"
    exit 1
fi

if [ ${#MSG} -lt 5 ]; then
    echo "❌ Сообщение слишком короткое (минимум 5 символов)"
    exit 1
fi

exit 0
```

```bash
chmod +x .git/hooks/commit-msg

git commit -m "fix"
❌ Сообщение слишком короткое (минимум 5 символов)

git commit -m "Add login form validation"
✅ [main abc123] Add login form validation
```

---

### pre-push — запустить тесты до push

Создай `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running tests before push..."

python -m pytest tests/ -q
if [ $? -ne 0 ]; then
    echo "❌ Тесты не прошли! Push отменён."
    exit 1
fi

echo "✅ Tests passed"
exit 0
```

```bash
chmod +x .git/hooks/pre-push

git push
Running tests before push...
15 passed in 3.2s
✅ Tests passed
Enumerating objects... done.
```

> **Совет:** pre-push хорош когда тесты быстрые (< 30 сек).
> Для долгих тестов — используй CI (GitHub Actions).

---

## 2.3 Хуки на сервере: post-receive

**post-receive** запускается на сервере после `git push`.

Это самый простой способ сделать автодеплой без GitHub Actions.

### Сценарий

```
Разработчик → git push → сервер (bare repo)
                              │
                              post-receive hook
                              │
                              cd /opt/myapp && git pull
                              docker compose build
                              docker compose up -d
```

### Настройка

#### 1. Создай bare репозиторий на сервере

```bash
ssh deploy@server
mkdir -p /opt/myapp.git
cd /opt/myapp.git
git init --bare
```

`--bare` = репозиторий без рабочей директории. Только git-данные.

#### 2. Создай рабочую директорию

```bash
mkdir -p /opt/myapp
cd /opt/myapp
git clone /opt/myapp.git .
```

#### 3. Создай post-receive хук

```bash
nano /opt/myapp.git/hooks/post-receive
```

```bash
#!/bin/bash
echo "🚀 Deploying..."

# Перейти в рабочую директорию
cd /opt/myapp

# Забрать новый код
git pull origin main

# Пересобрать и перезапустить
docker compose build app
docker compose up -d app

# Очистить старые образы
docker image prune -f

echo "✅ Deploy complete"
```

```bash
chmod +x /opt/myapp.git/hooks/post-receive
```

#### 4. На локальной машине добавь удалённый репозиторий

```bash
git remote add server deploy@server:/opt/myapp.git
git push server main
```

```
Enumerating objects... done.
Writing objects... done.

🚀 Deploying...
Already up to date.
[+] Building... done.
[+] Running 1/0
  Container myapp-app-1  Started
✅ Deploy complete
```

> **Запомни:** Это самый простой CI/CD. Один файл, одна команда.
> Но есть минусы: нет тестов, нет rollback, нет истории деплоев.
> Для продакшена — используй GitHub Actions (главы 3-7).

---

## 2.4 Ограничения git hooks

| Проблема | Что значит |
|----------|-----------|
| Не коммитятся | `.git/hooks/` не в репозитории |
| Только локально | Каждый разработчик должен настроить сам |
| Нет централизованного контроля | Можно обойти с `--no-verify` |

### Решение: pre-commit утилита

[pre-commit.com](https://pre-commit.com) — менеджер хуков которые коммитятся в репозиторий.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

```bash
pre-commit install
# Хуки теперь у всех в команде
```

> **Совет:** Для команды используй `pre-commit`.
> Для личного проекта — достаточно `.git/hooks/`.

---

## 📝 Упражнения

### Упражнение 2.1: pre-commit хук
**Задача:**
1. Создай `.git/hooks/pre-commit` который проверяет синтаксис Python
2. Попробуй закоммитить файл с ошибкой — хук отменил?
3. Попробуй с правильным файлом — хук пропустил?

### Упражнение 2.2: commit-msg хук
**Задача:**
1. Создай `.git/hooks/commit-msg` который проверяет длину сообщения
2. Попробуй `-m "fix"` — отменил?
3. Попробуй `-m "Add login feature"` — пропустил?

### Упражнение 2.3: post-receive деплой (если есть сервер)
**Задача:**
1. На сервере: создай bare repo `/opt/test.git`
2. Создай рабочую директорию `/opt/test`
3. Создай post-receive хук который делает `git pull` и выводит "Deployed!"
4. Локально: `git remote add server user@server:/opt/test.git`
5. `git push server main` — увидел "Deployed!"?

### Упражнение 2.4: pre-push с тестами
**Задача:**
1. Создай тест который падает
2. Создай `.git/hooks/pre-push` с `pytest`
3. `git push` — push отменён?
4. Почини тест — push прошёл?

---

## 📋 Чеклист главы 2

- [ ] Я понимаю что такое git hook и когда он запускается
- [ ] Я могу создать pre-commit хук
- [ ] Я могу создать commit-msg хук
- [ ] Я могу создать pre-push хук
- [ ] Я понимаю post-receive для автодеплоя
- [ ] Я могу настроить простой деплой через post-receive
- [ ] Я знаю ограничения хуков (не коммитятся, только локально)
- [ ] Я знаю про `pre-commit` утилиту для команды

**Всё отметил?** Переходи к Главе 3 — первый пайплайн в GitHub Actions.
