# Приложение B: Готовые скрипты

---

## B.1 health-monitor.sh

```bash
#!/bin/bash
set -euo pipefail
source /etc/alerting.env

HOSTNAME=$(hostname)
ALERTS=()

send_alert() {
    curl -s -X POST \
      "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      -d "chat_id=${TG_CHAT_ID}" \
      -d "text=$1" \
      -d "parse_mode=HTML" > /dev/null
}

# Диск
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
[ "$DISK_USAGE" -gt 80 ] && ALERTS+=("💾 Диск: ${DISK_USAGE}%")

# RAM
RAM_FREE=$(free | awk '/^Mem:/ {printf "%.0f", $4/$2*100}')
[ "$RAM_FREE" -lt 10 ] && ALERTS+=("🧠 RAM: свободно ${RAM_FREE}%")

# Приложение
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
[ "$HTTP_CODE" != "200" ] && ALERTS+=("🔴 Приложение: ${HTTP_CODE}")

# Docker
STOPPED=$(docker ps -a --filter "status=exited" --format "{{.Names}}" | tr '\n' ' ')
[ -n "$STOPPED" ] && ALERTS+=("🐳 Остановлены: ${STOPPED}")

# Отправить
if [ ${#ALERTS[@]} -gt 0 ]; then
    MSG="<b>⚠️ ${HOSTNAME}</b>\n"
    for a in "${ALERTS[@]}"; do MSG+="• $a\n"; done
    MSG+="\n⏰ $(date '+%Y-%m-%d %H:%M')"
    send_alert "$MSG"
fi
```

---

## B.2 daily-report.sh

```bash
#!/bin/bash
set -euo pipefail
source /etc/alerting.env

send_alert() {
    curl -s -X POST \
      "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      -d "chat_id=${TG_CHAT_ID}" \
      -d "text=$1" \
      -d "parse_mode=HTML" > /dev/null
}

DISK=$(df / | awk 'NR==2 {printf "%s/%s (%s%%)", $3, $2, $5}')
RAM=$(free | awk '/^Mem:/ {printf "%.1fGB/%.1fGB", $3/1048576, $2/1048576}')
UPTIME=$(uptime -p)
BANNED=$(fail2ban-client banned 2>/dev/null | wc -w)

MSG="📊 <b>Ежедневный отчёт</b>\n\n"
MSG+="• Аптайм: ${UPTIME}\n"
MSG+="• Диск: ${DISK}\n"
MSG+="• RAM: ${RAM}\n"
MSG+="• fail2ban: ${BANNED} IP\n"
MSG+="\n⏰ $(date '+%Y-%m-%d')"

send_alert "$MSG"
```

---

## B.3 notify-failure.sh

```bash
#!/bin/bash
source /etc/alerting.env

SERVICE_NAME="$1"

MSG="🔴 <b>Сервис упал!</b>\n"
MSG+="Сервис: ${SERVICE_NAME}\n"
MSG+="Сервер: $(hostname)\n"
MSG+="Время: $(date '+%Y-%m-%d %H:%M')"

curl -s -X POST \
  "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  -d "chat_id=${TG_CHAT_ID}" \
  -d "text=${MSG}" \
  -d "parse_mode=HTML" > /dev/null
```

В systemd unit:
```ini
[Service]
ExecStopPost=/usr/local/bin/notify-failure.sh %n
```

---

## B.4 /etc/fail2ban/jail.local

```ini
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
maxretry = 3
bantime  = 2h

[nginx-http-auth]
enabled = true

[nginx-req-limit]
enabled  = true
logpath  = /var/log/nginx/error.log
maxretry = 10
bantime  = 30m
```

---

## B.5 Cron файлы

### /etc/cron.d/health-monitor
```
*/5 * * * * root /usr/local/bin/health-monitor.sh >> /var/log/health-monitor.log 2>&1
```

### /etc/cron.d/daily-report
```
0 9 * * * root /usr/local/bin/daily-report.sh >> /var/log/daily-report.log 2>&1
```

### /etc/cron.d/docker-prune
```
0 4 * * 0 root docker system prune -f >> /var/log/docker-prune.log 2>&1
```
