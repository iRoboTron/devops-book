# DevOps: Путь с нуля до самостоятельности

## 🎯 Цель проекта

Научиться DevOps с абсолютного нуля до уровня, когда я могу **самостоятельно**, без помощи ИИ:

- Развернуть Python-проект на сервере (Ubuntu)
- Настроить автоматический деплой из Git (push → автообновление на сервере)
- Настроить Nginx, HTTPS, домен
- Контейнеризовать приложение в Docker
- Настроить CI/CD пайплайн
- Обеспечить мониторинг, бэкапы и безопасность

## 📋 Стартовые условия

- **Опыт:** программист, знаю только 3 команды консоли Linux
- **Сервер:** Ubuntu, стоит Nextcloud
- **Проект для деплоя:** Python-приложение (парень делает сайт на Python)
- **Желаемый workflow:** разработчик пушит в Git → сервер сам подхватывает и обновляется

## 🗺️ Карта обучения

### Модуль 0: Подготовка окружения
- Поднять виртуалку (VirtualBox + Ubuntu Server)
- Настроить SSH-доступ
- Создать тестового пользователя, разобраться с правами

### Модуль 1: Linux для DevOps
- Файловая система, права (`chmod`, `chown`, `umask`)
- Процессы и сервисы (`ps`, `top`, `systemctl`, `journalctl`)
- Сеть (`ss`, `curl`, `nc`, `iptables` базово)
- Диски (`df`, `du`, `mount`, `fstab`)
- Логи и их анализ
- Пользователи и группы

### Модуль 2: Сеть для DevOps
- IP, порты, DNS, HTTP/HTTPS
- Reverse proxy (Nginx)
- SSL-сертификаты (Let's Encrypt, certbot)
- Фаервол (`ufw`)

### Модуль 3: Docker и контейнеризация
- Контейнеры vs виртуальные машины
- Dockerfile для Python-приложения
- docker-compose: мультиконтейнерные приложения
- Сети и тома в Docker
- Docker Hub, образы

### Модуль 4: CI/CD — непрерывная интеграция и доставка
- Git: ветки, merge, hooks (углублённо)
- GitHub Actions / GitLab CI: пайплайны
- Автоматический деплой по push в ветку
- Секреты и переменные окружения
- Стратегии деплоя (zero-downtime, rollback)

### Модуль 5: Инфраструктура на сервере
- Nginx как reverse proxy
- systemd сервисы
- Управление переменными окружения
- Базы данных (PostgreSQL) в Docker и на хосте
- Резервное копирование

### Модуль 6: Безопасность и мониторинг
- Пользователи, SSH-ключи, fail2ban
- Обновления и патчи
- Мониторинг ресурсов (htop, netdata)
- Логирование и алертинг
- Бэкапы и восстановление

### 🏆 Финальный проект
Развернуть реальный Python-проект на сервере:
1. Контейнеризация приложения
2. CI/CD пайплайн (push → тесты → сборка → деплой)
3. Автодеплой на сервер по push в Git
4. Nginx + HTTPS + домен
5. Мониторинг и бэкапы

## 📚 Как учимся

Каждый модуль проходит через 4 этапа:

1. **Теория** — коротко и по делу, зачем и почему
2. **Команды по одной** — не "стена текста", разбираем каждую команду
3. **Практика** — делаю на виртуалке/сервере своими руками
4. **Мини-тест** — объясняю что сделал и почему (для закрепления)

## 🚀 Текущий статус

На **25 апреля 2026 г.** ситуация такая:

- **Практика ещё не начата:** Модуль 0 по-прежнему ждёт поднятия виртуалки и первого SSH-доступа
- **Материалы курса уже собраны:** в `docs/books` есть книги и практические файлы для модулей 1–14
- **Курс DevOps 1.0 фактически заполнен:** Linux, Nginx/HTTPS, Docker, CI/CD, инфраструктура, безопасность и финальный playbook уже лежат в проекте
- **Курс DevOps 2.0 уже создан целиком, но неравномерно по глубине:** Terraform и часть базовых модулей проработаны заметно глубже, а Monitoring, GitOps и финальные проекты пока короче
- **Часть 3 Security Engineering создана:** модули 15–21 добавлены как отдельная серия книг про защиту, безопасные проверки и архитектуру безопасности
- **Каталоги книг нормализованы:** книги в `docs/books` теперь лежат в нумерованных директориях `01-...` ... `21-...`, а ридер и сайт подстроены под эту схему
- **Итоговый проект книги 2 переписан:** теперь он начинается с чистой Ubuntu, SSH, установки Python/Nginx/ufw, `requirements.txt`, `.venv`, `pip install`, Gunicorn, systemd, Nginx, HTTPS и мониторинга
- **Публичный ридер обновлён:** на `https://adelfos.ru/devops/` выложена новая структура книг, старые дубли на сайте убраны

## 📚 Курс DevOps 1.0 — Книги

> Статус ниже отражает **фактическое содержимое репозитория** на 12 апреля 2026 г., а не только изначальный план.

| Модуль | Книга | Инструкция для агента | Статус |
|--------|-------|-----------------------|--------|
| 1 | Linux для DevOps | [AGENT-INSTRUCTIONS.md](docs/books/AGENT-INSTRUCTIONS.md) | Книга в репозитории: 19 `.md` файлов, ~8.3k строк |
| 2 | Сеть для DevOps: Nginx, HTTPS, безопасность и Caddy | [AGENT-INSTRUCTIONS-module-02.md](docs/books/AGENT-INSTRUCTIONS-module-02.md) | Книга в репозитории: 14 `.md` файлов, ~5.5k строк |
| 3 | Docker для DevOps: Контейнеры, образы и Compose | [AGENT-INSTRUCTIONS-module-03.md](docs/books/AGENT-INSTRUCTIONS-module-03.md) | Книга в репозитории: 14 `.md` файлов, ~4.7k строк |
| 4 | CI/CD для DevOps: Автоматизация от push до продакшна | [AGENT-INSTRUCTIONS-module-04.md](docs/books/AGENT-INSTRUCTIONS-module-04.md) | Книга в репозитории: 14 `.md` файлов, ~4.1k строк |
| 5 | Инфраструктура сервера: База данных, бэкапы и надёжность | [AGENT-INSTRUCTIONS-module-05.md](docs/books/AGENT-INSTRUCTIONS-module-05.md) | Книга в репозитории: 14 `.md` файлов, ~3.8k строк |
| 6 | Безопасность и мониторинг: Защита, наблюдение и алертинг | [AGENT-INSTRUCTIONS-module-06.md](docs/books/AGENT-INSTRUCTIONS-module-06.md) | Книга в репозитории: 14 `.md` файлов, ~2.8k строк |
| 7 | Финальный проект: Production-сервер с нуля | [AGENT-INSTRUCTIONS-module-07.md](docs/books/AGENT-INSTRUCTIONS-module-07.md) | Практический модуль в репозитории: 3 `.md` файла, ~780 строк |

---

## 🚀 Курс DevOps 2.0 — Продвинутый уровень

**Цель:** закрыть навыки, которые реально требуют на собеседованиях — Kubernetes, Terraform, Ansible, Prometheus, GitOps.

**Предварительные требования:** полное прохождение DevOps 1.0.

**Объём:** ~180 часов практической работы.

### 🗺️ Карта обучения 2.0

#### Модуль 8: Terraform — Инфраструктура как код (~20 ч)
- Провайдеры, ресурсы, переменные, state-файл
- Modules, remote state, workspace (dev/staging/prod)
- Terraform + CI/CD: `plan` на PR, `apply` на merge
- 3 мини-проекта + danger zone: destroy/taint/import

#### Модуль 9: Ansible — Управление конфигурацией (~20 ч)
- Inventory, playbooks, модули (apt, copy, template, service)
- Roles, handlers, Vault для секретов
- Идемпотентность, тестирование ролей (Molecule)
- Terraform + Ansible: создать сервер и сразу настроить

#### Модуль 10: Kubernetes — Основы (~25 ч)
- Архитектура, Pod, Deployment, Service, ConfigMap, Secret
- Volume, Namespace, kubectl шпаргалка
- Локальный кластер: k3s
- 3 мини-проекта: деплой Python-приложения, rolling update, dev/prod namespace

#### Модуль 11: Kubernetes — Продвинутый + Helm (~25 ч)
- Ingress, HPA, ResourceRequests/Limits
- Helm: charts, создание своего chart
- StatefulSet, PersistentVolume, RBAC, NetworkPolicy
- 3 мини-проекта: Helm chart с БД, autoscaling, миграция docker-compose → K8s

#### Модуль 12: Prometheus + Grafana + Loki — Production-мониторинг (~25 ч)
- Метрики: counter, gauge, histogram; Node Exporter
- PromQL, Grafana дашборды
- Alertmanager: алерты в Telegram/Slack
- Loki + Promtail: агрегация логов; kube-prometheus-stack
- 3 мини-проекта: дашборд сервера, алерт на падение, поиск ошибок в Loki

#### Модуль 13: GitLab CI + GitOps — Продвинутый CI/CD (~25 ч)
- GitLab CI: `.gitlab-ci.yml`, Runner, Docker-in-Docker, Registry
- GitOps: ArgoCD, синхронизация K8s с Git
- ApplicationSet, progressive delivery (Canary, Blue-Green)
- 3 мини-проекта: CI пайплайн, ArgoCD автодеплой, Blue-green без даунтайма

#### Модуль 14: Финальные проекты (~40 ч)
4 серьёзных проекта, охватывающих весь стек 2.0:
1. **Production Python App** — Terraform → Ansible → K8s + Helm → Prometheus → GitLab CI/CD
2. **Микросервисная архитектура** — 3 сервиса в K8s, Ingress, GitOps через ArgoCD
3. **Disaster Recovery** — IaC для всего, симуляция падения, восстановление
4. **Platform Engineering** — GitLab + ArgoCD + Prometheus + Grafana = developer self-service

### 📚 Книги курса 2.0

> Статус ниже отражает **фактическое содержимое репозитория** на 12 апреля 2026 г., а не только изначальный план.

| Модуль | Книга | Инструкция для агента | Статус |
|--------|-------|-----------------------|--------|
| 8 | Terraform: Инфраструктура как код | [AGENT-INSTRUCTIONS-module-08.md](docs/books/AGENT-INSTRUCTIONS-module-08.md) | Книга в репозитории: 12 `.md` файлов, ~2.9k строк |
| 9 | Ansible: Управление конфигурацией | [AGENT-INSTRUCTIONS-module-09.md](docs/books/AGENT-INSTRUCTIONS-module-09.md) | Книга в репозитории: 12 `.md` файлов, ~1.5k строк |
| 10 | Kubernetes: Основы | [AGENT-INSTRUCTIONS-module-10.md](docs/books/AGENT-INSTRUCTIONS-module-10.md) | Книга в репозитории: 11 `.md` файлов, ~1.0k строк |
| 11 | Kubernetes: Продвинутый уровень и Helm | [AGENT-INSTRUCTIONS-module-11.md](docs/books/AGENT-INSTRUCTIONS-module-11.md) | Книга в репозитории: 12 `.md` файлов, ~1.1k строк |
| 12 | Prometheus + Grafana + Loki: Production-мониторинг | [AGENT-INSTRUCTIONS-module-12.md](docs/books/AGENT-INSTRUCTIONS-module-12.md) | Книга в репозитории: 10 `.md` файлов, ~540 строк |
| 13 | GitLab CI + GitOps: ArgoCD и продвинутый CI/CD | [AGENT-INSTRUCTIONS-module-13.md](docs/books/AGENT-INSTRUCTIONS-module-13.md) | Книга в репозитории: 8 `.md` файлов, ~400 строк |
| 14 | Финальные проекты: Production-инфраструктура с нуля | [AGENT-INSTRUCTIONS-module-14.md](docs/books/AGENT-INSTRUCTIONS-module-14.md) | Проекты в репозитории: 6 `.md` файлов, ~630 строк |

## 📝 Заметки и решения

Важные решения и знания буду сохранять в локальную память проекта.

## Session Logs

История сессий разработки: [SESSION-LOG.md](SESSION-LOG.md)

---

*Обучение началось 9 апреля 2026 г.*
*Инструкция для Модуля 2 добавлена 11 апреля 2026 г.*
*Инструкция для Модуля 3 добавлена 11 апреля 2026 г.*
*Инструкция для Модуля 4 добавлена 11 апреля 2026 г.*
*Инструкция для Модуля 5 добавлена 11 апреля 2026 г.*
*Инструкция для Модуля 6 добавлена 11 апреля 2026 г.*
*Инструкция для Модуля 7 (финальный проект) добавлена 12 апреля 2026 г. — курс 1.0 полностью спланирован.*
*Курс DevOps 2.0 спланирован 12 апреля 2026 г. — модули 8–14, инструкции для агента написаны.*
*README актуализирован по фактическому содержимому `docs/books` 12 апреля 2026 г.*
*Итоговый проект книги 2 переписан как самостоятельный сценарий с чистой Ubuntu 22 апреля 2026 г.*
