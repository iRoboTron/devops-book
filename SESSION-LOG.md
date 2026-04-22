# Session Log

<!-- новые записи СВЕРХУ -->

---

## [2026-04-22 13:19] — Книга 2: итоговый проект с чистой Ubuntu и savelog

### Что делали
Переписали итоговый проект второй книги "Сеть для DevOps" как автономный сценарий с чистой Ubuntu, сохранили итог в память, оформили `/savelog` и подготовили изменения к публикации в репозиторий.

### Итоговые команды
```bash
# Проверить состояние репозитория
git status --short --branch

# Проверить изменения итогового проекта
git diff --check -- docs/books/nginx-https-devops/chapter-09.md docs/books/nginx-https-devops/appendix-b.md docs/books/nginx-https-devops/book.md

# Сохранить краткую память по правке
mem-store "dev-ops: итоговый проект книги 2 переписан с чистой Ubuntu" "<резюме>" dev-ops

# Закоммитить и отправить первую часть правки книги 2
git add docs/books/nginx-https-devops/chapter-09.md docs/books/nginx-https-devops/appendix-b.md docs/books/nginx-https-devops/book.md
git commit -m "Rewrite network final project from scratch"
git push origin main
```

### Все команды сессии (хронология)
| Команда | Для чего |
|---------|---------|
| `pwd` | Проверить текущую директорию проекта |
| `rg -n "codex_apps|wham|mcp" ...` | Диагностировать ошибку MCP `codex_apps` |
| `env \| sort \| rg -n "CODEX|MCP|..."` | Найти признак отключенной сети в sandbox |
| `sed -n '109960,110000p' ~/.codex/log/codex-tui.log` | Прочитать фрагмент лога Codex с ошибками DNS/MCP |
| `rg -n "Итог|итог|финаль|проект|Python|pip|venv|requirements|Ubuntu|SSH" docs/books/nginx-https-devops` | Найти итоговый проект второй книги и пропущенные шаги |
| `git diff --check -- docs/books/nginx-https-devops/...` | Проверить Markdown-правки перед коммитом |
| `git add docs/books/nginx-https-devops/chapter-09.md docs/books/nginx-https-devops/appendix-b.md docs/books/nginx-https-devops/book.md` | Добавить в индекс только правки книги 2 |
| `git commit -m "Rewrite network final project from scratch"` | Создать коммит с переписанным итоговым проектом |
| `git push origin main` | Отправить коммит в `origin/main` |
| `mem-store "dev-ops: итоговый проект книги 2 переписан с чистой Ubuntu" ... dev-ops` | Сохранить итог в локальную память |
| `date '+%Y-%m-%d %H:%M %Z'` | Получить точное время для журнала |

### Что объясняли
- `codex_apps`: встроенный HTTP MCP-коннектор падает из-за сетевой/DNS-проблемы, а не из-за локальных MCP `filesystem` или `obsidian`.
- `requirements.txt`: файл фиксирует Python-библиотеки проекта, чтобы новый сервер можно было поднять повторяемо через `pip install -r requirements.txt`.
- `venv + gunicorn + systemd`: приложение не должно запускаться как `python3 app.py &`; серверный вариант — отдельный пользователь, `.venv`, Gunicorn и systemd.
- `/savelog`: текстовая инструкция в `config.toml` не обязательно становится slash-командой в интерфейсе; для переиспользования нужен оформленный skill.

### Решения
- Итоговый проект книги 2 сделан самостоятельным, без зависимости от проекта первой книги.
- Основной путь оставлен через Nginx, а Caddy оформлен как альтернатива после понимания Nginx.
- В первом коммите были включены только связанные файлы книги 2, чтобы не смешивать их с чужими/автогенерированными изменениями.
- Оставшиеся изменения пользователь попросил залить все, поэтому следующий коммит должен включать весь текущий dirty state проекта.

### Тупики
- `/save` не найден: в конфиге проекта описан `/savelog`, а не `/save`.
- `/savelog` не отображался как команда: локальный файл лежал как `skill.md`, а Codex skills ожидают `SKILL.md`.
- Первая попытка заменить `chapter-09.md` через удаление файла абсолютным путём не прошла; правка была сделана точечными patch-операциями.
- Первая проверка Markdown fences через `python3 -c` упала из-за кавычек в shell-команде; повторная команда с безопасным quoting прошла.

---
