# Приложение A: Шпаргалка команд

---

## SSH

| Команда | Что делает |
|---------|-----------|
| `sshd -t` | Проверить конфиг SSH |
| `systemctl reload sshd` | Применить без обрыва сессий |
| `ssh -L 19999:localhost:19999 user@server` | SSH-туннель |

---

## fail2ban

| Команда | Что делает |
|---------|-----------|
| `fail2ban-client status` | Общий статус |
| `fail2ban-client status sshd` | Статус SSH jail |
| `fail2ban-client banned` | Список забаненных IP |
| `fail2ban-client set sshd unbanip IP` | Разбанить IP |
| `journalctl -u fail2ban -f` | Логи в реальном времени |

---

## Обновления

| Команда | Что делает |
|---------|-----------|
| `unattended-upgrade --dry-run -v` | Что будет обновлено |
| `unattended-upgrade -d` | Запустить с отладкой |
| `needrestart` | Сервисы для перезапуска |

---

## lynis

| Команда | Что делает |
|---------|-----------|
| `lynis audit system` | Полный аудит |
| `lynis show details TEST_ID` | Детали проверки |

---

## Netdata

| Действие | Что делать |
|----------|-----------|
| Установка | `sh kickstart.sh --stable-channel --disable-telemetry` |
| Закрыть | `bind to = 127.0.0.1` в netdata.conf |
| Подключиться | `ssh -L 19999:localhost:19999 user@server` |

---

## Telegram

| Действие | Команда |
|----------|---------|
| Создать бота | @BotFather → `/newbot` |
| Узнать chat_id | `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` |
| Отправить | `curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" -d "chat_id=ID" -d "text=MSG"` |

---

## logwatch

| Команда | Что делает |
|---------|-----------|
| `logwatch --output stdout --range today` | Дайджест за сегодня |
| `logwatch --detail med` | Средняя детализация |
| `logwatch --range yesterday` | За вчера |

---

## goaccess

| Команда | Что делает |
|---------|-----------|
| `goaccess access.log --log-format=COMBINED` | Анализ Nginx логов |
