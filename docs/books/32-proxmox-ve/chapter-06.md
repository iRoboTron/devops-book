# Глава 6: Community Scripts — магазин приложений для Proxmox

> **Что вы узнаете:**
> - что такое Community Scripts и почему это не просто удобство, а реальная экономия времени;
> - как безопасно запускать скрипты из интернета — смотреть исходник до запуска;
> - как установить Uptime Kuma одной командой и с нуля вручную;
> - что делать если скрипт недоступен или устарел.

---

## 6.1 Что такое Community Scripts

Когда вы только устанавливаете Proxmox, перед вами сотни популярных сервисов, которые хотелось бы запустить: Docker с Portainer, Home Assistant, Nextcloud, Jellyfin, менеджер паролей, мониторинг. Каждый из них нужно установить в отдельный LXC, настроить зависимости, включить systemd, проверить что работает.

Это можно делать вручную. А можно использовать **Community Scripts** — коллекцию bash-скриптов, которую поддерживает сообщество Proxmox.

Сайт проекта: **https://community-scripts.github.io/ProxmoxVE/**

Каждый скрипт делает одно и то же по стандартной схеме:

1. Создаёт LXC-контейнер с нужными параметрами (нужное количество RAM, диска, нужные флаги).
2. Скачивает и устанавливает ПО.
3. Настраивает systemd-сервис для автозапуска.
4. В конце выводит IP-адрес и порт — куда идти в браузере.

Вместо 30 минут ручной настройки — одна команда и 2-5 минут ожидания.

Сегодня в репозитории более 200 готовых скриптов, которые активно обновляются под актуальные версии ПО.

---

## 6.2 Как пользоваться Community Scripts

Все скрипты запускаются **на хосте Proxmox** из Shell. Открыть Shell: в веб-интерфейсе выбрать узел (pve) → кнопка **Shell** в верхней панели.

Общий формат команды:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/<script-name>.sh)"
```

Разберём что здесь происходит:

- `curl -fsSL <url>` — скачивает скрипт по HTTPS, флаги `-f` прерывает при ошибке HTTP, `-s` без прогресс-бара, `-S` показывает ошибки, `-L` следует редиректам.
- `$( ... )` — подстановка: результат curl передаётся как строка.
- `bash -c "..."` — выполняет полученную строку как bash-скрипт.

После запуска скрипт задаёт вопросы в интерактивном режиме: использовать настройки по умолчанию или задать своё (RAM, объём диска, CTID). Для большинства задач — нажимать Enter и принимать дефолты.

**Пример: установка Docker LXC.**

```bash
# На хосте Proxmox в Shell — эта команда создаёт LXC с Docker и Portainer
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/docker.sh)"
```

Скрипт задаст вопросы:

```
This will create a New Docker LXC.
Proceed? (y/n): y
Using Default Settings
 Advanced Settings? (y/n): n
Creating a Docker LXC using the above default settings
```

Через несколько минут:

```
Docker LXC successfully created
IP Address: 192.168.1.105
```

Открываете в браузере `http://192.168.1.105:9000` — там уже Portainer.

---

## 6.3 Таблица популярных скриптов

| Сервис | Что устанавливает | RAM по умолчанию | Порт |
|--------|------------------|-----------------|------|
| Docker LXC | LXC + Docker CE + Portainer | 2 GB | 9000 (Portainer) |
| Home Assistant OS | VM с официальным HAOS | 2 GB balloon | 8123 |
| Nextcloud | LXC с Nextcloud AIO | 2 GB | 8080 |
| Jellyfin | LXC с медиасервером | 2 GB | 8096 |
| Nginx Proxy Manager | LXC с reverse proxy + UI | 1 GB | 81 (admin) |
| Vaultwarden | LXC с self-hosted Bitwarden | 256 MB | 8000 |
| Gitea | LXC с self-hosted Git | 1 GB | 3000 |
| AdGuard Home | LXC с DNS-фильтром рекламы | 512 MB | 3000 |
| Uptime Kuma | LXC с мониторингом сервисов | 1 GB | 3001 |
| Netdata | LXC с мониторингом хоста | 1 GB | 19999 |
| Tailscale | Установка Tailscale на хост | — | — |
| Proxmox Backup Server | VM или LXC с PBS | 2 GB | 8007 |

Актуальный список с командами установки — на сайте проекта. Скрипты могут меняться, поэтому всегда берите команду с сайта, а не из старых статей.

---

## 6.4 Что происходит под капотом скрипта

Прежде чем запускать скрипт от имени root на своём сервере — полезно понять что именно он делает.

Типичный скрипт Community Scripts работает так:

```
1. Скачивает вспомогательные функции (build.func)
2. Задаёт переменные: CTID, RAM, диск, шаблон ОС
3. Вызывает pct create с нужными параметрами
4. Запускает контейнер
5. Выполняет внутри LXC: apt update, установку ПО, настройку systemd
6. Выводит IP и сообщение об успехе
```

---

## 6.5 Как смотреть исходник перед запуском

Запускать код из интернета от имени root без проверки — плохая практика. Это правило работает и для Community Scripts, хотя репозиторий надёжный.

**Способ 1 — через браузер.** На сайте https://community-scripts.github.io/ProxmoxVE/ у каждого скрипта есть ссылка на GitHub. Нажмите на название — открывается исходник прямо на GitHub.

**Способ 2 — через curl в терминале.** Перед запуском скачайте скрипт и прочитайте:

```bash
# Скачать скрипт и просмотреть постранично — не запуская
curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptime-kuma.sh | less
```

Нажмите `q` чтобы выйти из `less`. Если скрипт выглядит понятно и не делает ничего подозрительного — можно запускать.

**Что проверять:**

- Какую ОС использует для LXC (debian, ubuntu — норма).
- Откуда скачивает ПО (официальные репозитории или GitHub-релизы — норма; незнакомые домены — повод насторожиться).
- Не меняет ли конфиги за пределами контейнера (в надёжных скриптах — не меняет).
- Не открывает ли лишних портов на хосте.

**Способ 3 — сохранить в файл, проверить, запустить.**

```bash
# Скачать скрипт в файл
curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptime-kuma.sh \
  -o /tmp/uptime-kuma.sh

# Просмотреть
less /tmp/uptime-kuma.sh

# Если всё нормально — запустить вручную
bash /tmp/uptime-kuma.sh
```

Этот способ также помогает когда нужно изменить параметры по умолчанию — например, задать конкретный CTID или нестандартный объём диска.

---

## 6.6 Ручные альтернативы — план Б

Скрипты могут быть временно недоступны: DNS-проблемы, смена URL репозитория, устаревший скрипт после обновления ПО. Поэтому важно уметь установить основные сервисы вручную.

### Docker LXC вручную

Этот способ подробно описан в Главе 4, здесь — краткое напоминание:

```bash
# 1. Создать privileged LXC с Debian 12 через веб-интерфейс
#    CT → Options → Features → включить Nesting и Keyctl
#    (или через CLI: --features keyctl=1,nesting=1 --unprivileged 0)

# 2. Запустить и войти в контейнер
pct start 100 && pct enter 100

# 3. Внутри LXC — установить Docker официальным скриптом
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# 4. Проверить
docker run hello-world
```

Итог: Docker работает в LXC, можно запускать любые контейнеры.

### Nginx Proxy Manager вручную

Nginx Proxy Manager (NPM) — reverse proxy с веб-интерфейсом, автоматическими SSL-сертификатами и простой настройкой через браузер. Разворачивается в LXC с Docker:

```bash
# Внутри LXC с Docker
mkdir -p /opt/npm && cd /opt/npm

# Создать docker-compose.yml для NPM
cat > docker-compose.yml << 'EOF'
services:
  npm:
    image: jc21/nginx-proxy-manager:latest
    restart: unless-stopped
    ports:
      - "80:80"      # HTTP-трафик
      - "443:443"    # HTTPS-трафик
      - "81:81"      # Веб-интерфейс NPM
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
EOF

# Запустить
docker compose up -d

# Проверить статус
docker compose ps
```

Через 30-60 секунд открыть `http://IP-LXC:81`. Логин по умолчанию: `admin@example.com` / `changeme`. При первом входе система попросит сменить пароль.

### Uptime Kuma вручную

Uptime Kuma — мониторинг доступности сервисов. Поддерживает HTTP, TCP, ping, DNS. Уведомления в Telegram, Email, Slack и другие. Для домашнего сервера — идеальный выбор: лёгкий, красивый интерфейс, не требует базы данных.

**Вариант А: через Docker (если уже есть LXC с Docker):**

```bash
# Одна команда внутри любого LXC с Docker —
# создаёт контейнер, монтирует том для данных, включает автозапуск
docker run -d \
  --name uptime-kuma \
  --restart always \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:latest
```

**Вариант Б: Node.js напрямую в LXC (без Docker):**

```bash
# Внутри LXC с Debian 12
apt update && apt install -y nodejs npm git

# Клонировать и установить зависимости
git clone https://github.com/louislam/uptime-kuma.git /opt/uptime-kuma
cd /opt/uptime-kuma
npm install --production

# Создать systemd-сервис для автозапуска
cat > /etc/systemd/system/uptime-kuma.service << 'EOF'
[Unit]
Description=Uptime Kuma
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/uptime-kuma
ExecStart=/usr/bin/node server/server.js
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now uptime-kuma
```

Открыть `http://IP-LXC:3001` — первый вход предложит создать учётную запись администратора.

---

## 6.7 Практика: установка Uptime Kuma через Community Scripts

Uptime Kuma — хорошая первая практика с Community Scripts: скрипт небольшой, сервис понятный, результат виден сразу.

### Шаг 1: Прочитать исходник

Перед запуском — посмотреть что делает скрипт:

```bash
# На хосте Proxmox в Shell
curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptimekuma.sh | less
```

В скрипте увидите: создание LXC с Debian, установку Node.js, клонирование репозитория Uptime Kuma, создание systemd-сервиса. Всё ожидаемо.

### Шаг 2: Запустить скрипт

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptimekuma.sh)"
```

Скрипт задаст вопросы — для начала принимайте настройки по умолчанию:

```
This will create a New Uptime-Kuma LXC.
Proceed? (y/n): y
Using Default Settings
 Advanced Settings? (y/n): n
```

Дождитесь завершения. В конце увидите:

```
Uptime-Kuma LXC successfully created
IP Address: 192.168.1.106
```

### Шаг 3: Открыть в браузере

Перейдите на `http://192.168.1.106:3001`. Если IP другой — посмотреть в веб-интерфейсе Proxmox: LXC → Summary → IP.

При первом входе Uptime Kuma предложит создать учётную запись. Придумайте логин и пароль.

### Шаг 4: Добавить первый монитор

В интерфейсе Uptime Kuma:

1. Нажать **Add New Monitor**.
2. Monitor Type: **HTTP(s)**.
3. Friendly Name: `Proxmox Web`.
4. URL: `https://192.168.1.100:8006` (IP вашего Proxmox).
5. Нажать **Save**.

Через несколько секунд монитор покажет статус: зелёный (UP) если Proxmox доступен.

Добавьте ещё несколько мониторов — для каждого LXC и VM на вашем сервере.

### Шаг 5: Настроить уведомления в Telegram (опционально)

В Uptime Kuma: **Settings → Notifications → Add Notification**:

1. Тип: Telegram.
2. Bot Token: получить у `@BotFather` в Telegram командой `/newbot`.
3. Chat ID: написать боту `@userinfobot`, он пришлёт ваш ID.
4. Нажать **Test** — в Telegram придёт тестовое сообщение.

Теперь если любой из мониторов упадёт — придёт уведомление в Telegram.

---

## 6.8 Типичные ошибки

**Ошибка: скрипт завершился с ошибкой, LXC не создан.**

```
[ERROR] Failed to download CT template
```

Причина: не настроен бесплатный репозиторий или нет доступа в интернет.

Решение:
```bash
# Проверить доступ в интернет с хоста
ping -c 3 8.8.8.8

# Проверить что шаблоны скачиваются
pveam update
pveam available | grep debian
```

---

**Ошибка: порт занят, сервис не запускается.**

```
Error: bind EADDRINUSE 0.0.0.0:3001
```

Причина: на этом LXC уже запущен другой сервис на том же порту, или вы запустили второй экземпляр.

Решение: проверить что занимает порт внутри LXC:
```bash
pct enter <CTID>
ss -tlnp | grep 3001
```

---

**Ошибка: Community Scripts недоступен — URL не отвечает.**

Причина: DNS, firewall, или изменился URL репозитория.

Проверить:
```bash
curl -v https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/uptimekuma.sh 2>&1 | head -20
```

Решение: использовать ручную установку (см. раздел 6.6) или зайти на GitHub и найти актуальный URL скрипта.

---

**Ошибка: создан дублирующий LXC с тем же CTID.**

```
CT 100 already exists
```

Причина: скрипт запущен повторно, а контейнер с таким ID уже есть.

Решение: при повторном запуске выбрать Advanced Settings и указать другой CTID, или удалить существующий контейнер:
```bash
pct stop 100 && pct destroy 100
```

---

## Чек-лист для самопроверки

- [ ] Прочитал исходник скрипта через `curl | less` перед запуском
- [ ] Установил хотя бы один сервис через Community Scripts
- [ ] Uptime Kuma открывается в браузере, добавлен первый монитор
- [ ] Могу установить Docker LXC вручную без скрипта (помню три шага)
- [ ] Знаю как развернуть Nginx Proxy Manager вручную через docker-compose
