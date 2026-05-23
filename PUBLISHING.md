# Как устроен проект и как публиковать книги

## Структура репозитория

```
dev-ops/
├── docs/
│   └── books/                      ← всё содержимое сайта
│       ├── index.html              ← каталог книг (главная страница)
│       ├── reader.html             ← читалка (открывает главы)
│       ├── files.json              ← список всех книг и глав
│       ├── 01-linux-for-devops/    ← папка книги
│       │   ├── book.md             ← оглавление книги
│       │   ├── chapter-00.md
│       │   ├── chapter-01.md
│       │   └── appendix-a.md
│       ├── 32-proxmox-ve/          ← книга 32
│       │   └── ...
│       └── AGENT-INSTRUCTIONS-module-XX.md  ← ТЗ для агента (не деплоится)
└── PUBLISHING.md                   ← этот файл
```

## Как устроен сайт

**Адрес:** https://adelfos.ru/devops/

**Сервер:** Jino хостинг, SSH-алиас `jino`

**Docroot на сервере:**
```
domains/adelfos.ru/public_html/devops/     ← index.html, reader.html, files.json
domains/adelfos.ru/public_html/devops/books/ ← папки книг (01-linux..., 32-proxmox...)
```

Обрати внимание: `index.html`, `reader.html`, `files.json` лежат в **корне** `devops/`, а папки книг — в `devops/books/`. Локально всё лежит в `docs/books/`, но на сервере разделено.

**Как работает каталог:**
1. `index.html` загружает `files.json?v=ASSET_VERSION` (version для сброса кэша)
2. Для каждой книги ищет метаданные в `COURSE_META` внутри `index.html`
3. Рендерит карточки по секциям (`PARTS` — массив с диапазонами номеров)

**Как работает читалка:**
- URL: `reader.html?b=32&c=book` → книга с номером 32, файл book.md
- Параметр `b` — **номер из имени папки** (32 для `32-proxmox-ve`)
- Параметр `c` — имя файла без `.md` (`book`, `1`, `2`, `a`, `b`...)

---

## Добавить новую книгу — чеклист

### Шаг 1: Создать папку и файлы книги

```bash
mkdir docs/books/NN-book-name
```

Обязательные файлы:
- `book.md` — оглавление (заголовок + список ссылок на главы)
- `chapter-00.md`, `chapter-01.md`, ... — главы
- `appendix-a.md`, `appendix-b.md`, ... — приложения (если есть)

### Шаг 2: Добавить книгу в `files.json`

Файл: `docs/books/files.json`

Структура — объект `courses`, ключ = имя папки:

```json
{
  "courses": {
    "01-linux-for-devops": [...],
    "NN-book-name": [
      {"file": "book.md",       "title": "Название книги"},
      {"file": "chapter-00.md", "title": "Глава 0: ..."},
      {"file": "chapter-01.md", "title": "Глава 1: ..."},
      {"file": "appendix-a.md", "title": "Приложение A: ..."}
    ]
  }
}
```

Порядок файлов в массиве — порядок отображения в оглавлении.

### Шаг 3: Добавить метаданные в `index.html`

Файл: `docs/books/index.html`

Найти блок `const COURSE_META = {` и добавить запись:

```js
"NN-book-name": {
    title: "Короткое название",
    label: "Подзаголовок карточки",
    description: "Описание книги для каталога (2-3 предложения).",
    tags: ["тег1", "тег2", "тег3"],
    color: "#0969da",   // цвет шапки карточки
    icon: "server"      // иконка (см. список ниже)
},
```

**Доступные иконки:** `terminal`, `globe`, `box`, `flow`, `server`, `shield`, `rocket`, `blocks`, `wand`, `hex`, `cubes`, `chart`, `branch`, `mountain`, `wall`

### Шаг 4: Обновить диапазон части (если нужно)

В `index.html` найти блок `const PARTS = [` и проверить что новый номер попадает в нужную часть:

```js
{ id: 'misc', title: 'Часть 4. Прочее', from: 22, to: 32 }
//                                                     ↑ обновить если добавляем книгу 33+
```

### Шаг 5: Обновить ASSET_VERSION в обоих файлах

**Критически важно** — иначе браузеры отдадут кэш и книга не появится.

В `docs/books/index.html`:
```js
const ASSET_VERSION = 'YYYYMMDD-short-description';
// пример: '20260523-book-32-proxmox'
```

В `docs/books/reader.html` — то же самое значение:
```js
const ASSET_VERSION = 'YYYYMMDD-short-description';
```

### Шаг 6: Задеплоить на сервер

```bash
# 1. Обновить index.html, reader.html, files.json в КОРНЕ devops/
rsync -avz docs/books/index.html docs/books/reader.html docs/books/files.json \
  jino:domains/adelfos.ru/public_html/devops/

# 2. Загрузить папку книги в devops/books/
rsync -avz docs/books/NN-book-name/ \
  jino:domains/adelfos.ru/public_html/devops/books/NN-book-name/
```

⚠️ **Частая ошибка:** деплоить `index.html` в `devops/books/` вместо корня `devops/`. На сайте будет отображаться старый каталог.

### Шаг 7: Проверить

```bash
# Проверить что сайт отвечает
curl -s -o /dev/null -w "%{http_code}" https://adelfos.ru/devops/
# Должно быть: 200

# Проверить что файл книги доступен
curl -s -o /dev/null -w "%{http_code}" https://adelfos.ru/devops/books/NN-book-name/book.md
# Должно быть: 200

# Проверить что files.json обновился (новый ASSET_VERSION)
curl -s "https://adelfos.ru/devops/files.json?v=ASSET_VERSION" | python3 -m json.tool | grep NN-book-name
```

### Шаг 8: Закоммитить и запушить

```bash
git add docs/books/NN-book-name/ docs/books/files.json docs/books/index.html docs/books/reader.html
git commit -m "Add book NN: Название книги"
git push origin main
```

Репозиторий: `git@github-irobotron:iRoboTron/devops-book.git`

---

## Быстрый деплой (только обновление существующей книги)

Если правишь только главы уже опубликованной книги — достаточно:

```bash
rsync -avz docs/books/NN-book-name/ \
  jino:domains/adelfos.ru/public_html/devops/books/NN-book-name/
```

`index.html`, `reader.html`, `files.json` трогать не нужно.

---

## Нумерация книг

- Номер берётся из имени папки: `32-proxmox-ve` → номер 32
- Книги могут иметь пропуски в нумерации (30, 32 — нормально)
- Читалка ищет книгу по номеру из имени папки, не по позиции в списке
- Нельзя использовать одинаковые номера

---

## Типовые иконки по теме

| Тема | Иконка |
|------|--------|
| Linux, терминал | `terminal` |
| Сеть, сайт | `globe` |
| Docker, контейнеры | `box` |
| CI/CD, пайплайн | `flow` |
| Сервер, инфраструктура | `server` |
| Безопасность | `shield` |
| Kubernetes, кластер | `cubes` |
| Мониторинг, метрики | `chart` |
| Git, ветки | `branch` |
| Proxmox, виртуализация | `cubes` |
| Архитектура | `blocks` |
| Финальный проект | `rocket` |

---

## Типовые цвета карточек

| Цвет | Hex | Когда |
|------|-----|-------|
| Синий | `#0969da` | Базовые темы, Linux, Docker |
| Зелёный | `#1a7f37` | Сеть, деплой, Ansible |
| Фиолетовый | `#8250df` | CI/CD, Kubernetes |
| Красный | `#cf222e` | Безопасность |
| Жёлто-коричневый | `#9a6700` | Прочее, коммуникация |
| Тёмно-синий | `#0550ae` | Terraform, инфраструктура |
