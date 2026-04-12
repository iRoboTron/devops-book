# Глава 7: Переменные окружения и секреты

> **Запомни:** Пароли в docker-compose.yml = пароли в git = пароли для всего мира. Никогда не хардкодь секреты.

---

## 7.1 Почему нельзя хардкодить секреты

### Плохо

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: supersecret123    ← ПАРОЛЬ В КОДЕ
```

**Проблемы:**
- Файл в git → пароль в истории
- Разработчик видит пароль продакшена
- Невозможно поменять без изменения кода
- Образ содержит пароль в слоях

### Хорошо

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}    ← из переменной
```

Пароль в `.env` файле. `.env` в `.gitignore`.

---

## 7.2 Три способа передать переменные

```
1. environment: в docker-compose.yml  → только для несекретных
2. .env файл + ${VAR} в compose       → секреты на сервере
3. env_file: директива                → весь файл переменных в контейнер
```

---

## 7.3 `.env` файл

Создай `.env` рядом с `docker-compose.yml`:

```env
# .env
POSTGRES_PASSWORD=supersecret123
POSTGRES_USER=myapp_user
POSTGRES_DB=myapp_db
SECRET_KEY=abc123def456
DATABASE_URL=postgresql://myapp_user:supersecret123@db:5432/myapp_db
```

В `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_DB: ${POSTGRES_DB}

  app:
    build: .
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SECRET_KEY: ${SECRET_KEY}
```

> **Запомни:** `${VAR}` подставляется из `.env` при запуске `docker compose up`.
> docker compose сам читает `.env` из той же директории.

---

## 7.4 `.gitignore` — `.env` ВСЕГДА в игноре

```bash
# .gitignore
.env
```

> **Опасно:** Один `git add .env` — и секрет навсегда в истории git.
> Даже если потом удалить — он в истории коммитов.
> 
> Правило: `.env` в `.gitignore` с ПЕРВОГО коммита.

### `.env.example` — шаблон для команды

Создай `.env.example` с пустыми значениями:

```env
# .env.example — скопируй в .env и заполни значения
POSTGRES_PASSWORD=
POSTGRES_USER=
POSTGRES_DB=
SECRET_KEY=
DATABASE_URL=
```

Этот файл **можно** коммитить. Разработчик скопирует и заполнит:

```bash
cp .env.example .env
nano .env  # заполнить значения
```

---

## 7.5 `env_file:` — передать весь файл

Вместо перечисления каждой переменной:

```yaml
services:
  app:
    build: .
    env_file:
      - .env
```

Все переменные из `.env` попадут в контейнер.

### Разные файлы для разных сред

```yaml
services:
  app:
    build: .
    env_file:
      - .env           # общие переменные
      - .env.local     # локальные переопределения
```

---

## 7.6 `docker compose config` — проверить

```bash
docker compose config
```

Показывает финальный конфиг с **подставленными** переменными:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: supersecret123    ← видно значение!
      POSTGRES_USER: myapp_user
```

> **Опасно:** `docker compose config` показывает секреты!
> Не копи вывод если там есть пароли.

### Без секретов

```bash
docker compose config --no-normalize
```

Покажет `${VAR}` вместо значений.

---

## 7.7 Переопределение переменных

### Приоритет (от высшего к низшему)

1. Переменные окружения хоста (`export VAR=val`)
2. `.env` файл
3. Значения по умолчанию в compose (`${VAR:-default}`)

### Значение по умолчанию

```yaml
environment:
  POSTGRES_USER: ${POSTGRES_USER:-postgres}
  POSTGRES_DB: ${POSTGRES_DB:-mydb}
```

Если `.env` не задан — используется значение после `:-`.

---

## 7.8 Полный пример с секретами

### .env

```env
POSTGRES_PASSWORD=x7k9mP2qR5wN
POSTGRES_USER=app_user
POSTGRES_DB=app_db
SECRET_KEY=django-insecure-abc123def456
DEBUG=false
```

### .env.example

```env
POSTGRES_PASSWORD=
POSTGRES_USER=
POSTGRES_DB=
SECRET_KEY=
DEBUG=true
```

### .gitignore

```
.env
```

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG}
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend

volumes:
  pgdata:

networks:
  backend:
```

---

## 📝 Упражнения

### Упражнение 7.1: Создать .env
**Задача:**
1. Создай `.env` файл:
   ```env
   POSTGRES_PASSWORD=testpass123
   POSTGRES_USER=testuser
   POSTGRES_DB=testdb
   ```
2. Создай `.env.example` (пустой)
3. Добавь `.env` в `.gitignore`
4. Проверь: `git status` — `.env` не tracked?

### Упражнение 7.2: Использовать в compose
**Задача:**
1. Измени docker-compose.yml чтобы использовать `${VAR}`
2. Проверь: `docker compose config` — переменные подставились?
3. Подними: `docker compose up -d`
4. Проверь что БД создалась с правильным пользователем

### Упражнение 7.3: Значения по умолчанию
**Задача:**
1. Измени compose:
   ```yaml
   environment:
     POSTGRES_USER: ${POSTGRES_USER:-defaultuser}
     POSTGRES_DB: ${POSTGRES_DB:-defaultdb}
   ```
2. Переименуй `.env` → `.env.bak`
3. `docker compose config` — какие значения используются?
4. Верни `.env` на место

### Упражнение 7.4: env_file
**Задача:**
1. Создай отдельный файл `app.env`:
   ```env
   DEBUG=false
   LOG_LEVEL=info
   MY_CUSTOM_VAR=hello
   ```
2. Добавь в compose:
   ```yaml
   app:
     env_file:
       - app.env
   ```
3. Зайди в контейнер: `docker compose exec app bash`
4. Проверь: `echo $MY_CUSTOM_VAR`

### Упражнение 7.5: DevOps Think
**Задача:** «Ты случайно закоммитил `.env` с паролями в git. Что делать?»

Ответ:
1. НЕМЕДЕННО поменяй все пароли в `.env`
2. Удали `.env` из git: `git rm --cached .env`
3. Добавь в `.gitignore`: `.env`
4. Закоммить: `git commit -m "Remove .env from tracking"`
5. Пароли всё ещё в истории git — считай их скомпрометированными
6. В будущем: используй pre-commit хук чтобы `.env` не попадал в коммиты

---

## 📋 Чеклист главы 7

- [ ] Я понимаю почему нельзя хардкодить секреты в compose
- [ ] Я могу создать `.env` файл с переменными
- [ ] Я могу использовать `${VAR}` в docker-compose.yml
- [ ] Я добавил `.env` в `.gitignore`
- [ ] Я создал `.env.example` как шаблон
- [ ] Я могу использовать `env_file:` для передачи всех переменных
- [ ] Я могу проверить конфиг через `docker compose config`
- [ ] Я понимаю приоритет переменных (хост > .env > default)
- [ ] Я знаю что делать если случайно закоммитил `.env`

**Всё отметил?** Переходи к Главе 8 — Nginx в Docker и полный стек.
