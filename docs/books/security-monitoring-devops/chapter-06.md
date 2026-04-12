# Глава 6: Алерты в Telegram

> **Запомни:** Email часто не читают сразу. Telegram — мгновенно. Для алертов с одного сервера — идеальный вариант.

---

## 6.1 Создать Telegram-бота

1. Открой Telegram
2. Найди `@BotFather`
3. Напиши `/newbot`
4. Выбери имя (например `MyServer Monitor`)
5. Выбери username (например `myapp_monitor_bot`)
6. Получишь **токен**: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

> **Опасно:** Токен = пароль от бота. Не коммить в git!

---

## 6.2 Узнать свой chat_id

1. Напиши боту `/start`
2. Открой: `https://api.telegram.org/bot<ТОКЕН>/getUpdates`
3. Найди `"chat":{"id":123456789}`

Или через curl:

```bash
curl "https://api.telegram.org/bot<ТОКЕН>/getUpdates" | grep -o '"id":[0-9]*'
```

`123456789` = твой `chat_id`.

---

## 6.3 Хранить секреты

```bash
sudo nano /etc/alerting.env
```

```
TG_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_CHAT_ID=123456789
```

```bash
sudo chmod 600 /etc/alerting.env
sudo chown root:root /etc/alerting.env
```

---

## 6.4 Функция отправки

```bash
send_alert() {
    local message="$1"
    curl -s -X POST \
      "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      -d "chat_id=${TG_CHAT_ID}" \
      -d "text=${message}" \
      -d "parse_mode=HTML" > /dev/null
}
```

Использование:

```bash
send_alert "🔴 Сервер упал!"
```

---

## 6.5 health-monitor.sh — полный скрипт

Создай `/usr/local/bin/health-monitor.sh`:

```bash
#!/bin/bash
set -euo pipefail
source /etc/alerting.env

HOSTNAME=$(hostname)
ALERTS=()

# Функция отправки
send_alert() {
    local message="$1"
    curl -s -X POST \
      "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      -d "chat_id=${TG_CHAT_ID}" \
      -d "text=${message}" \
      -d "parse_mode=HTML" > /dev/null
}

# Диск
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
    ALERTS+=("💾 Диск: ${DISK_USAGE}% (порог 80%)")
fi

# RAM
RAM_FREE=$(free | awk '/^Mem:/ {printf "%.0f", $4/$2*100}')
if [ "$RAM_FREE" -lt 10 ]; then
    ALERTS+=("🧠 RAM: свободно ${RAM_FREE}% (порог 10%)")
fi

# Приложение
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    ALERTS+=("🔴 Приложение: healthcheck вернул ${HTTP_CODE}")
fi

# Docker-контейнеры
STOPPED=$(docker ps -a --filter "status=exited" --format "{{.Names}}" | tr '\n' ' ')
if [ -n "$STOPPED" ]; then
    ALERTS+=("🐳 Остановлены контейнеры: ${STOPPED}")
fi

# fail2ban
BANNED=$(sudo fail2ban-client banned 2>/dev/null | wc -w)
if [ "$BANNED" -gt 10 ]; then
    ALERTS+=("🔒 fail2ban: заблокировано ${BANNED} IP")
fi

# Отправить если есть алерты
if [ ${#ALERTS[@]} -gt 0 ]; then
    MESSAGE="<b>⚠️ Сервер: ${HOSTNAME}</b>\n\n"
    for alert in "${ALERTS[@]}"; do
        MESSAGE+="• ${alert}\n"
    done
    MESSAGE+="\n⏰ $(date '+%Y-%m-%d %H:%M')"
    send_alert "$MESSAGE"
fi
```

```bash
sudo chmod +x /usr/local/bin/health-monitor.sh
```

---

## 6.6 Cron: каждые 5 минут

```bash
sudo nano /etc/cron.d/health-monitor
```

```
*/5 * * * * root /usr/local/bin/health-monitor.sh >> /var/log/health-monitor.log 2>&1
```

---

## 6.7 Алерт при падении сервиса

Создай `/usr/local/bin/notify-failure.sh`:

```bash
#!/bin/bash
source /etc/alerting.env

SERVICE_NAME="$1"

MESSAGE="🔴 <b>Сервис упал!</b>\n"
MESSAGE+="Сервис: ${SERVICE_NAME}\n"
MESSAGE+="Сервер: $(hostname)\n"
MESSAGE+="Время: $(date '+%Y-%m-%d %H:%M')"

curl -s -X POST \
  "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "text=${MESSAGE}" \
  -d "parse_mode=HTML" > /dev/null
```

```bash
sudo chmod +x /usr/local/bin/notify-failure.sh
```

Добавь в `.service` файл:

```ini
[Service]
ExecStopPost=/usr/local/bin/notify-failure.sh %n
```

---

## 6.8 Ежедневный отчёт

Создай `/usr/local/bin/daily-report.sh`:

```bash
#!/bin/bash
set -euo pipefail
source /etc/alerting.env

HOSTNAME=$(hostname)
UPTIME=$(uptime -p)
DISK=$(df / | awk 'NR==2 {printf "%s/%s (%s%%)", $3, $2, $5}')
RAM=$(free | awk '/^Mem:/ {printf "%.1fGB/%.1fGB", $3/1048576, $2/1048576}')
BACKUP_STATUS="OK"  # проверить последний бэкап
BANNED=$(sudo fail2ban-client banned 2>/dev/null | wc -w)

MESSAGE="📊 <b>Ежедневный отчёт: ${HOSTNAME}</b>\n\n"
MESSAGE+="• Аптайм: ${UPTIME}\n"
MESSAGE+="• Диск: ${DISK}\n"
MESSAGE+="• RAM: использовано ${RAM}\n"
MESSAGE+="• Бэкап: ${BACKUP_STATUS}\n"
MESSAGE+="• fail2ban: заблокировано ${BANNED} IP за сутки\n"
MESSAGE+="\n⏰ $(date '+%Y-%m-%d')"

curl -s -X POST \
  "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "text=${MESSAGE}" \
  -d "parse_mode=HTML" > /dev/null
```

```bash
sudo chmod +x /usr/local/bin/daily-report.sh
```

### Cron: раз в день в 9:00

```bash
sudo nano /etc/cron.d/daily-report
```

```
0 9 * * * root /usr/local/bin/daily-report.sh >> /var/log/daily-report.log 2>&1
```

---

## 6.9 Алерт при деплое

Добавь в CI/CD workflow (Модуль 4):

```yaml
- name: Notify Telegram
  run: |
    curl -s -X POST \
      "https://api.telegram.org/bot${{ secrets.TG_TOKEN }}/sendMessage" \
      -d "chat_id=${{ secrets.TG_CHAT_ID }}" \
      -d "text=✅ Деплой завершён: ${GITHUB_SHA}" \
      -d "parse_mode=HTML"
  env:
    TG_TOKEN: ${{ secrets.TG_TOKEN }}
    TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
```

---

## 📝 Упражнения

### Упражнение 6.1: Создать бота
**Задача:**
1. Создай бота через @BotFather
2. Узнай chat_id через `/getUpdates`
3. Создай `/etc/alerting.env` с токеном и chat_id
4. Права: `chmod 600 /etc/alerting.env`

### Упражнение 6.2: Тестовый алерт
**Задача:**
1. Создай скрипт отправки:
   ```bash
   source /etc/alerting.env
   curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
     -d "chat_id=${TG_CHAT_ID}" \
     -d "text=Test alert!"
   ```
2. Получил сообщение в Telegram? ✅

### Упражнение 6.3: health-monitor.sh
**Задача:**
1. Создай `/usr/local/bin/health-monitor.sh`
2. Запусти вручную: `sudo /usr/local/bin/health-monitor.sh`
3. Алерт пришёл? (должен если есть проблемы)
4. Добавь в cron: `/etc/cron.d/health-monitor`

### Упражнение 6.4: Ежедневный отчёт
**Задача:**
1. Создай `daily-report.sh`
2. Запусти вручную — пришёл отчёт?
3. Добавь в cron на 9:00

### Упражнение 6.5: DevOps Think
**Задача:** «Telegram-бот перестал отправлять алерты. Как диагностировать?»

Подсказки:
1. Токен правильный? `cat /etc/alerting.env`
2. Интернет работает? `curl https://api.telegram.org`
3. Бот не заблокирован? Попробуй вручную отправить
4. cron работает? `grep CRON /var/log/syslog`
5. Скрипт запускается? `cat /var/log/health-monitor.log`

---

## 📋 Чеклист главы 6

- [ ] Telegram-бот создан
- [ ] Токен и chat_id в `/etc/alerting.env` с правами 600
- [ ] Тестовое сообщение пришло
- [ ] health-monitor.sh создан и работает
- [ ] Cron для health-monitor (каждые 5 минут)
- [ ] daily-report.sh создан
- [ ] Cron для daily-report (9:00)
- [ ] notify-failure.sh для systemd сервисов

**Всё отметил?** Переходи к Главе 7 — логи и logwatch.
