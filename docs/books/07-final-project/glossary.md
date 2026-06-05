# Глоссарий

> Термины и выражения итогового проекта Модуля 1. В скобках — где встречается.

---

**Capstone-проект** — итоговый практический проект, собирающий весь production-стек заново на чистом сервере без опоры на учебные книги 2-6. _(book, playbook)_

**Playbook** — пошаговый сценарий настройки сервера: команды по фазам, порядок строго сверху вниз. _(book, playbook)_

**Фаза** — логический этап playbook (Ф0–Ф14), каждый завершается проверкой и опирается на предыдущий. _(playbook)_

**VPS** — виртуальный частный сервер; рекомендуемая стартовая точка проекта — новый VPS с чистой Ubuntu. _(book)_

**A-запись** — DNS-запись, связывающая домен с IP сервера; должна указывать на сервер до запуска Caddy для авто-SSL. _(book, playbook)_

**root-доступ** — права суперпользователя, нужны только на первичную настройку; затем работа идёт под пользователем deploy. _(book, playbook)_

**deploy (пользователь)** — непривилегированный системный пользователь, под которым работают Docker, деплой и cron-задачи. _(playbook, checklist)_

**SSH-ключ (ed25519)** — пара ключей для беспарольного входа; публичный кладётся в `authorized_keys`, приватный хранится у клиента. _(playbook)_

**authorized_keys** — файл со списком разрешённых публичных SSH-ключей пользователя. _(playbook)_

**SSH hardening** — усиление настроек SSH: `PermitRootLogin no`, `PasswordAuthentication no`, `MaxAuthTries 3`. _(playbook, checklist)_

**ufw** — Uncomplicated Firewall, простой фаервол Ubuntu; в проекте открыты только порты 22, 80, 443. _(book, playbook, checklist)_

**Docker** — система контейнеризации; ставится официальным скриптом `get.docker.com`. _(book, playbook)_

**docker-compose.yml** — декларативное описание сервисов (app, db) с сетями, томами и healthcheck. _(playbook)_

**healthcheck** — встроенная проверка живости контейнера; для app — `curl /health`, для db — `pg_isready`. _(playbook, checklist)_

**Named volume (pgdata)** — именованный том Docker, хранящий данные PostgreSQL и переживающий пересоздание контейнера. _(book, playbook)_

**PostgreSQL** — реляционная СУБД проекта (образ `postgres:16-alpine`), данные в volume pgdata. _(book, playbook)_

**.env** — файл переменных окружения (пароли, токены, DOMAIN, IMAGE_TAG); права 600. _(playbook, checklist)_

**chmod 600** — права «чтение и запись только владельцу»; обязательны для `.env` и `alerting.env`. _(playbook, checklist)_

**Caddy** — reverse proxy с автоматическим выпуском Let's Encrypt-сертификатов и редиректом HTTP→HTTPS. _(book, playbook)_

**reverse_proxy** — проксирование входящих HTTPS-запросов на внутренний порт приложения (8000). _(book, playbook)_

**Авто-SSL** — автоматический выпуск и продление TLS-сертификатов Caddy без ручного вмешательства. _(book, playbook)_

**GHCR (ghcr.io)** — GitHub Container Registry, хранилище Docker-образов приложения. _(playbook)_

**PAT (Personal Access Token)** — токен GitHub для логина в GHCR; нужны права `read:packages` / `write:packages`. _(playbook)_

**IMAGE_TAG** — переменная с тегом образа; CI подставляет в неё SHA коммита для конкретной версии. _(playbook, checklist)_

**Миграции БД** — обновление схемы базы: `alembic upgrade head` (FastAPI) или `manage.py migrate` (Django). _(playbook)_

**rclone** — утилита синхронизации файлов с облаком; в проекте отправляет бэкапы в Backblaze B2. _(playbook, checklist)_

**Backblaze B2** — S3-совместимое облачное хранилище для офсайт-бэкапов. _(book, playbook)_

**backup.sh** — скрипт бэкапа: pg_dump → gzip → проверка → конфиги → rclone в облако → очистка старых. _(playbook, checklist)_

**pg_dump** — штатная утилита PostgreSQL для выгрузки дампа базы данных. _(playbook)_

**cron.d** — каталог системных cron-заданий; здесь `myapp-backup` (03:00) и `myapp-monitor` (каждые 5 мин). _(playbook, checklist)_

**fail2ban** — сервис, банящий IP после серии неудачных попыток входа; jail `sshd` обязателен. _(book, playbook, checklist)_

**jail.local** — пользовательский конфиг fail2ban с параметрами bantime, findtime, maxretry и списком jail'ов. _(playbook)_

**unattended-upgrades** — автоматическая установка security-обновлений пакетов Ubuntu. _(playbook, checklist)_

**Netdata** — система мониторинга метрик в реальном времени; привязана к 127.0.0.1, доступ через SSH-туннель. _(book, playbook, checklist)_

**SSH-туннель** — проброс локального порта (`ssh -L 19999:localhost:19999`) для доступа к Netdata без открытия порта наружу. _(playbook, checklist)_

**health-monitor.sh** — скрипт-страж: каждые 5 минут шлёт в Telegram алерт при проблеме (диск, RAM, health, контейнеры). _(playbook, checklist)_

**Telegram-алерт** — уведомление через Bot API (`sendMessage`) с использованием TG_TOKEN и TG_CHAT_ID. _(book, playbook, checklist)_

**alerting.env** — отдельный файл с токенами Telegram (права 600), подключаемый скриптами мониторинга. _(playbook)_

**GitHub Actions** — CI/CD-платформа; workflow из трёх job'ов: test → build → deploy. _(book, playbook, checklist)_

**Workflow (deploy.yml)** — описание пайплайна в `.github/workflows`, запускается на push в main. _(playbook)_

**Repository Secret** — зашифрованный секрет GitHub (SERVER_HOST, SSH_PRIVATE_KEY, GHCR_TOKEN) для workflow. _(playbook)_

**appleboy/ssh-action** — action, выполняющий деплой-команды на сервере по SSH из workflow. _(playbook)_

**docker compose pull / up -d** — обновление сервиса: загрузить новый образ и перезапустить контейнер в фоне. _(playbook, checklist)_

**docker image prune** — очистка неиспользуемых образов, чтобы не забивать диск после деплоев. _(playbook, checklist)_

**Production-ready** — состояние стенда, прошедшего 28–30 из 30 проверок чеклиста. _(checklist)_
