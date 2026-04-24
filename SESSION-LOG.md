# Session Log

<!-- новые записи СВЕРХУ -->

---

## [2026-04-25 01:35] — Нумерация каталогов книг, публикация части 3 и /save

### Что делали
Привели книги к нумерованной структуре каталогов, обновили ридер и публикацию на `adelfos.ru`, почистили сайт от дублей и служебных файлов, затем добавили локальный алиас `/save` к workflow `savelog`.

### Итоговые команды
```bash
# Проверить текущую структуру и ссылки ридера
git status --short
git remote -v
rg -n "fetch\\(|COURSE_NAMES|COURSE_ALIASES|files.json" docs/books/index.html docs/books/reader.html

# Переименовать каталоги книг в нумерованный вид и пересобрать индекс
cd docs/books
mv linux-for-devops 01-linux-for-devops
mv nginx-https-devops 02-nginx-https-devops
mv docker-devops 03-docker-devops
# ... аналогично для остальных книг до 21
python3 generate_filelist.py

# Зафиксировать переименование и обновление ридера
git add -A docs/books
git commit -m "Renumber book directories and sync reader paths"
git push origin main

# Добавить cache-busting для ридера
git add docs/books/index.html docs/books/reader.html
git commit -m "Bust cache for book reader assets"
git push origin main

# Выложить сайт в реальный docroot
rsync -az docs/books/.htaccess docs/books/*.html docs/books/*.json docs/books/*.md docs/books/*.py jino:domains/adelfos.ru/public_html/devops/
rsync -az docs/books/[0-9][0-9]-* jino:domains/adelfos.ru/public_html/devops/books/

# Удалить старые каталоги и служебные файлы с сайта
ssh jino

# Проверить публикацию
curl -fsSL 'https://adelfos.ru/devops/files.json?v=20260424-1d2ae69'
curl -fsSL 'https://adelfos.ru/devops/reader.html'
curl -I -fsSL 'https://adelfos.ru/devops/books/01-linux-for-devops/book.md?v=20260424-1d2ae69'
```

### Все команды сессии (хронология)
| Команда | Для чего |
|---------|---------|
| `git status --short` | Проверить dirty state перед переименованием книг |
| `rg --files docs/books ...` | Просмотреть структуру `docs/books` и набор каталогов |
| `sed -n '260,520p' docs/books/index.html` | Прочитать логику загрузки файлов в ридере |
| `sed -n '320,620p' docs/books/reader.html` | Прочитать логику загрузки файлов в ридере |
| `python3 - <<'PY' ... files.json ... PY` | Быстро извлечь список ключей курсов из `files.json` |
| `find docs/books -maxdepth 1 -mindepth 1 -type d` | Сверить фактические каталоги курсов |
| `python3 - <<'PY' ... replace old slugs ... PY` | Обновить служебные markdown-документы под новую нумерацию |
| `python3 generate_filelist.py` | Пересобрать `files.json` после переименования каталогов |
| `git diff --check -- docs/books/...` | Проверить, что служебные файлы и ридер не сломаны |
| `git commit -m "Renumber book directories and sync reader paths"` | Зафиксировать массовое переименование и обновление ридера |
| `git push origin main` | Отправить коммит с новой структурой каталогов |
| `ssh jino '...'` | Найти реальный docroot сайта и проверить структуру на хостинге |
| `rsync -az ... jino:domains/adelfos.ru/devops/` | Первая публикация в неверный каталог на хостинге |
| `curl -i -fsSL https://adelfos.ru/devops/files.json` | Проверить, какую версию `files.json` реально отдает сайт |
| `git commit -m "Bust cache for book reader assets"` | Зафиксировать cache-busting для `reader.html` и `index.html` |
| `rsync -az ... jino:domains/adelfos.ru/public_html/devops/` | Выложить сайт в правильный docroot |
| `curl -fsSL 'https://adelfos.ru/devops/files.json?v=20260424-1d2ae69'` | Подтвердить, что с query string сайт отдает новые нумерованные ключи |
| `ssh jino 'rm -rf ...'` | Удалить ошибочно залитую копию сайта и старые ненумерованные каталоги |
| `sed -n '1,240p' ~/.codex/skills/savelog/SKILL.md` | Прочитать инструкцию skill `savelog` |
| `sed -n '1,220p' ~/.codex/config.toml` | Проверить, как настроена локальная команда `/savelog` |
| `sed -n '90,130p' ~/.claude/CLAUDE.md` | Сверить локальное правило про `/save` |
| `date '+%Y-%m-%d %H:%M %Z'` | Получить точное время для новой записи журнала |

### Что объясняли
- нумерованные каталоги книг: удобнее искать модули и однозначно сортировать их в файловой системе;
- ридер книг: ключи курсов берутся из `files.json`, а не из названий папок сами по себе, поэтому после rename нужно синхронно править `files.json`, `COURSE_NAMES`, `COURSE_ALIASES` и загрузку markdown;
- cache-busting: даже после `rsync` прокси/браузер может отдавать старые `reader.html` и `files.json`, поэтому версия в query string надежнее принудительно обновляет клиент;
- docroot сайта: `domains/adelfos.ru/devops` и `domains/adelfos.ru/public_html/devops` — разные каталоги, и сайт реально обслуживался из `public_html/devops`;
- `/save` и `/savelog`: workflow один и тот же, но для удобства пользователя нужен короткий alias `/save`, оформленный как отдельный invocable skill.

### Решения
- каталоги книг переведены в схему `01-...` ... `21-...`, чтобы навигация по репозиторию и серверу была предсказуемой;
- в `reader.html` и `index.html` добавлен fallback на две схемы путей (`books/<course>/<file>` и `<course>/<file>`), чтобы ридер работал и локально, и на сайте;
- для публикации выбран реальный docroot `domains/adelfos.ru/public_html/devops`, а ошибочная копия `domains/adelfos.ru/devops` удалена;
- со сайта удалены `AGENT-INSTRUCTIONS*.md` и прочие authoring-файлы, чтобы публичная директория содержала только то, что нужно ридеру;
- локально для Codex добавлен alias `/save`, а `/savelog` сохранен для обратной совместимости.

### Тупики
- первая заливка ушла в `domains/adelfos.ru/devops`, но сайт читал `domains/adelfos.ru/public_html/devops`;
- после корректной публикации `files.json` по обычному URL еще некоторое время отдавался из старого кэша, поэтому пришлось добавить `ASSET_VERSION` и query string;
- `/save` не существовал как отдельная команда: в локальном Codex-конфиге был описан только `/savelog`, поэтому alias пришлось оформить явно.

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
