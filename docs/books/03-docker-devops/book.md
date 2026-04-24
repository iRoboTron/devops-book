# Docker для DevOps: Контейнеры, образы и Compose

> Книга 3 курса DevOps: Путь с нуля до самостоятельности

---

## Оглавление

### Подготовка

- [**Глава 0: Зачем Docker и чем он отличается от виртуалки**](chapter-00.md)
  - Проблема "у меня работает", ВМ vs контейнер, ключевые понятия, установка

### Часть 1: Образы и контейнеры

- [**Глава 1: Первый контейнер**](chapter-01.md)
  - `docker run`, жизненный цикл, `docker ps`, `docker logs`, `docker exec`

- [**Глава 2: Образы**](chapter-02.md)
  - Слои, Docker Hub, теги, `docker pull`, `docker images`, почему не `latest`

- [**Глава 3: Dockerfile — написать свой образ**](chapter-03.md)
  - `FROM`, `WORKDIR`, `COPY`, `RUN`, `CMD`, кэш слоёв, `.dockerignore`

### Часть 2: Данные и сеть

- [**Глава 4: Тома (Volumes) — данные которые не исчезают**](chapter-04.md)
  - Volume, bind mount, `docker volume`, бэкап тома

- [**Глава 5: Сети Docker**](chapter-05.md)
  - Типы сетей, custom bridge, DNS между контейнерами, Docker и ufw

### Часть 3: Docker Compose

- [**Глава 6: docker-compose — весь стек одной командой**](chapter-06.md)
  - YAML-основы, services, volumes, networks, `depends_on`, healthcheck

- [**Глава 7: Переменные окружения и секреты**](chapter-07.md)
  - `.env`, `env_file`, `.gitignore`, `docker-compose config`

### Часть 4: Продакшн и практика

- [**Глава 8: Nginx в Docker и полный стек**](chapter-08.md)
  - Nginx в compose, две сети, SSL из хоста, `restart: unless-stopped`

- [**Глава 9: Итоговый проект**](chapter-09.md)
  - Новый Docker-проект на отдельной Docker-VM: `/opt/myapp`, app + db + nginx, Makefile, чеклист готовности

### Приложения

- [**Приложение A: Шпаргалка команд**](appendix-a.md)
- [**Приложение B: Готовые шаблоны**](appendix-b.md)
- [**Приложение C: Диагностика**](appendix-c.md)

---

## Что читатель построит к концу книги

```
docker-compose up -d
        │
        ├── [nginx:80] ← ./nginx/conf.d/app.conf
        │       │ proxy_pass
        │       ▼
        ├── [python-app:8000] ← Dockerfile (твой код)
        │       │ DATABASE_URL
        │       ▼
        └── [postgres:5432] ← volume: pgdata
                │
                └── volume: pgdata (данные не теряются при restart)
```

---

## Главная идея

Docker решает одну проблему: **"у меня работает, у тебя не работает"**.

- Образ = воспроизводимая упаковка приложения
- Контейнер = запущенная копия образа
- Dockerfile = рецепт сборки
- docker-compose = оркестрация нескольких контейнеров
- Volume = данные которые переживают контейнер
- Network = как контейнеры видят друг друга

---

## Как пользоваться книгой

1. **Читай по порядку** — главы построены друг на друге
2. **Смотри схемы** — ASCII-диаграммы показывают архитектуру
3. **Делай упражнения** — теория без практики мертва
4. **Отмечай чеклисты** — в конце каждой главы
5. **Понимай "зачем"** — не просто копируй команды

## Предварительные требования

- Пройдены Модули 1 и 2 (Linux + Сеть/Nginx)
- Установленная Ubuntu Server
- Для итогового проекта — новая Docker-VM или свободный порт 80 без host Nginx из книги 2
- Умение: `systemctl`, `nano`, `curl`, базовая сеть

---

*Docker для DevOps — Курс DevOps, Модуль 3*
