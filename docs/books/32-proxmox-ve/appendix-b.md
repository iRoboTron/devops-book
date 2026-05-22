# Приложение B: Рекомендуемые Community Scripts

> Community Scripts (https://community-scripts.org/) — коллекция bash-скриптов сообщества Proxmox. Каждый скрипт создаёт LXC или VM и устанавливает нужный сервис автоматически.
>
> **Перед запуском любого скрипта:** прочитать исходник через `curl -fsSL <url> | less` или на GitHub по адресу https://github.com/community-scripts/ProxmoxVE

---

## B.1 Как использовать

Все скрипты запускаются из Shell хоста Proxmox одной командой:

```bash
bash -c "$(curl -fsSL <url-скрипта>)"
```

Скрипт задаст вопросы (ID контейнера, RAM, диск) — можно оставить значения по умолчанию или настроить. В конце выведет IP и порт для доступа к сервису.

---

## B.2 Инфраструктура и управление

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Docker LXC** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"` | — | LXC с Docker + Portainer. Привилегированный контейнер с nesting и keyctl. Основа для запуска любых Docker-сервисов |
| **Portainer CE** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/portainer.sh)"` | `:9000` | Веб-интерфейс для управления Docker контейнерами. Удобнее чем командная строка для начинающих |
| **Nginx Proxy Manager** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/nginx-proxy-manager.sh)"` | `:81` | Reverse proxy с веб-интерфейсом, автоматические Let's Encrypt сертификаты через ACME, поддержка DuckDNS |
| **Traefik** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/traefik.sh)"` | `:8080` | Современный reverse proxy с автоматическим TLS. Альтернатива NPM для продвинутых пользователей |
| **Caddy** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/caddy.sh)"` | `:80/:443` | Простой web-сервер с автоматическим HTTPS. Минимальная конфигурация |

---

## B.3 Мониторинг и диагностика

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Uptime Kuma** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptimekuma.sh)"` | `:3001` | Мониторинг сервисов: HTTP, TCP, ping, DNS. Уведомления в Telegram, Discord, Slack. Красивый дашборд статусов |
| **Netdata** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/netdata.sh)"` | `:19999` | Мониторинг хоста в реальном времени: CPU, RAM, диски, сеть, процессы. Без настройки, сразу показывает графики |
| **Grafana** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/grafana.sh)"` | `:3000` | Профессиональные дашборды и графики. Требует источника данных (InfluxDB или Prometheus) |
| **InfluxDB** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/influxdb.sh)"` | `:8086` | Time-series БД для метрик. Используется вместе с Grafana или Telegraf |
| **Prometheus** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/prometheus.sh)"` | `:9090` | Система сбора метрик для продвинутого мониторинга |
| **Proxmox Backup Server** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/proxmox-backup-server.sh)"` | `:8007` | Инкрементальные бэкапы с дедупликацией. Значительно экономит место при частых бэкапах |

---

## B.4 Файловые сервисы и хранилище

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Nextcloud** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/nextcloud.sh)"` | `:443` | Личное облако: файлы, фото, календарь, контакты. AIO (All-In-One) образ, всё в одном |
| **Vaultwarden** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/vaultwarden.sh)"` | `:8080` | Self-hosted менеджер паролей, совместимый с Bitwarden. Работает с официальными клиентами Bitwarden |
| **Syncthing** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/syncthing.sh)"` | `:8384` | Синхронизация файлов между устройствами напрямую без облака. Аналог Dropbox, но self-hosted |
| **Filebrowser** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/filebrowser.sh)"` | `:8080` | Простой веб-файловый менеджер. Позволяет просматривать и скачивать файлы с сервера через браузер |

---

## B.5 Медиа и развлечения

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Jellyfin** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/jellyfin.sh)"` | `:8096` | Медиасервер с трансляцией видео и музыки. Бесплатная альтернатива Plex. Поддерживает hardware transcoding через GPU passthrough |
| **Plex** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/plex.sh)"` | `:32400` | Популярный медиасервер с красивым интерфейсом. Для расширенных функций нужна подписка Plex Pass |
| **Navidrome** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/navidrome.sh)"` | `:4533` | Музыкальный стриминг-сервер. Поддерживает протокол Subsonic — работает с большинством мобильных клиентов |
| **Kavita** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/kavita.sh)"` | `:5000` | Сервер для чтения книг (epub, pdf, cbz/cbr). Собственная библиотека с удобным ридером |

---

## B.6 Сеть и безопасность

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **AdGuard Home** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/adguard.sh)"` | `:3000` | DNS-сервер с блокировкой рекламы и трекеров. Настраивается как DNS-сервер в роутере — блокирует рекламу для всей сети |
| **Pi-hole** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/pihole.sh)"` | `:80` | Классическая альтернатива AdGuard Home. DNS-блокировщик для всей домашней сети |
| **Tailscale** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/tailscale.sh)"` | — | WireGuard VPN для безопасного удалённого доступа. Можно установить на хост или в отдельный LXC как subnet router |
| **WireGuard** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/wireguard.sh)"` | — | Самостоятельный VPN-сервер. Больше контроля чем Tailscale, но требует ручной настройки клиентов |
| **Crowdsec** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/crowdsec.sh)"` | — | Современная замена Fail2ban. Защита от брутфорса с коллективным блэклистом IP |

---

## B.7 Разработка и DevOps

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Gitea** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/gitea.sh)"` | `:3000` | Self-hosted Git-сервер. Аналог GitHub/GitLab, но лёгкий. Поддерживает pull requests, issues, CI/CD |
| **GitLab CE** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/gitlab.sh)"` | `:80` | Полноценная DevOps платформа. Требует значительных ресурсов (минимум 4GB RAM) |
| **Drone CI** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/drone.sh)"` | `:80` | CI/CD система. Подключается к Gitea или GitHub |
| **code-server** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/code-server.sh)"` | `:8080` | VS Code в браузере. Полноценная IDE доступная с любого устройства через браузер |

---

## B.8 Умный дом и IoT

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Home Assistant OS** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/vm/haos-vm.sh)"` | `:8123` | Официальный образ HAOS в VM. Рекомендованный способ запуска Home Assistant на Proxmox |
| **Home Assistant (LXC)** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/homeassistant-core.sh)"` | `:8123` | Home Assistant Core в LXC-контейнере. Занимает меньше ресурсов, но не поддерживает Supervisor и официальные add-ons |
| **Mosquitto MQTT** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/mosquitto.sh)"` | `:1883` | MQTT-брокер для IoT-устройств. Обязателен если использовать Zigbee2MQTT или ESP-устройства |
| **Zigbee2MQTT** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/zigbee2mqtt.sh)"` | `:8080` | Мост между Zigbee-устройствами и Home Assistant через MQTT. Нужен USB Zigbee-адаптер |
| **Node-RED** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/node-red.sh)"` | `:1880` | Визуальное программирование для автоматизаций. Используется вместе с Home Assistant |

---

## B.9 Прочие полезные сервисы

| Сервис | Команда | Доступ | Описание |
|--------|---------|--------|---------|
| **Paperless-ngx** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/paperless-ngx.sh)"` | `:8000` | Управление документами с OCR. Сканирует и индексирует PDF, автоматически распознаёт текст |
| **Immich** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/immich.sh)"` | `:2283` | Self-hosted Google Photos. Автозагрузка с телефона, распознавание лиц, поиск по фото |
| **Mealie** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/mealie.sh)"` | `:9000` | Менеджер рецептов с планировщиком меню и списком покупок. Импортирует рецепты по URL |
| **IT-Tools** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/it-tools.sh)"` | `:80` | Коллекция онлайн-инструментов для разработчиков: base64, UUID, JWT decode, cron editor и другие |
| **Stirling PDF** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/stirling-pdf.sh)"` | `:8080` | Self-hosted PDF-редактор: объединять, разделять, конвертировать, сжимать PDF |
| **Whoogle** | `bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/whoogle.sh)"` | `:5000` | Приватный поисковик: результаты Google без трекинга и рекламы |

---

## B.10 Замечания по использованию

**Перед запуском скрипта:**

```bash
# Посмотреть что именно делает скрипт — не запускать вслепую
curl -fsSL <url-скрипта> | less
```

**Если скрипт временно недоступен:**

DNS или firewall могут блокировать доступ к GitHub. Действия:
1. Проверить DNS: `curl -v https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh`
2. Скачать скрипт заранее на локальную машину и перенести на Proxmox.
3. Использовать ручную установку — все основные сервисы описаны в тексте книги.

**Ресурсы по умолчанию:**

Скрипты создают контейнеры с минимальными ресурсами. После установки проверить реальное потребление и увеличить лимиты при необходимости:

```bash
pct set <vmid> --memory 1024    # увеличить RAM
pct set <vmid> --cores 2        # увеличить CPU
pct resize <vmid> rootfs +10G   # расширить диск
```

**Обновления установленных сервисов:**

Community Scripts регулярно обновляются. Многие скрипты при повторном запуске предложат обновить сервис до последней версии — это безопасно.
