# Глава 2: fail2ban — автоматическая блокировка

> **Запомни:** fail2ban читает логи, находит атаки, блокирует IP. Ты спишь — он работает.

---

## 2.1 Что такое fail2ban

```
Лог: sshd: Failed password from 1.2.3.4
Лог: sshd: Failed password from 1.2.3.4
Лог: sshd: Failed password from 1.2.3.4
     ... (5 попыток)
fail2ban: IP 1.2.3.4 заблокирован на 1 час
iptables: DROP все пакеты от 1.2.3.4
```

fail2ban = автоматический охранник.

### Как работает

```
/var/log/auth.log ──→ fail2ban ──→ iptables
     логи              ищет            банит
                       паттерны        IP
```

---

## 2.2 Установка

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

### Проверить статус

```bash
sudo fail2ban-client status
Status
|- Number of jail:  1
`- Jail list:       sshd
```

---

## 2.3 Конфигурация: jail.local

**НЕ трогай `jail.conf`!** Он перезаписывается при обновлении.

Создай `jail.local`:

```bash
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
# На сколько банить
bantime  = 1h

# За какой период считать попытки
findtime = 10m

# Сколько попыток до бана
maxretry = 5

# IP которые никогда не банятся
ignoreip = 127.0.0.1/8 ::1

# Действие при бане (iptables + email)
action = %(action_mw)s

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
maxretry = 3
bantime  = 2h

[nginx-http-auth]
enabled = true
port    = http,https
logpath = /var/log/nginx/error.log

[nginx-req-limit]
enabled  = true
filter   = nginx-req-limit
logpath  = /var/log/nginx/error.log
maxretry = 10
bantime  = 30m
```

### Разбор

| Параметр | Значение |
|----------|----------|
| `bantime` | Сколько банить (1h = 1 час) |
| `findtime` | За какой период считать попытки |
| `maxretry` | Сколько попыток до бана |
| `ignoreip` | IP которые НЕ банятся (твой!) |

### Перезапустить

```bash
sudo systemctl restart fail2ban
```

---

## 2.4 Управление

### Общий статус

```bash
sudo fail2ban-client status
```

### Статус конкретного jail

```bash
sudo fail2ban-client status sshd
Status for the jail: sshd
|- Filter
|  |- Currently failed:  3
|  |- Total failed:      247
`- Actions
   |- Currently banned:  12
   |- Total banned:      89
   |- Banned IP list:    1.2.3.4 5.6.7.8 ...
```

### Разбанить IP

```bash
sudo fail2ban-client set sshd unbanip 1.2.3.4
```

### Список всех заблокированных

```bash
sudo fail2ban-client banned
```

### Логи fail2ban

```bash
sudo journalctl -u fail2ban -f
```

---

## 2.5 Защита от брутфорса веб-форм

fail2ban может защищать Nginx от брутфорса логин-форм.

### Кастомный фильтр

```bash
sudo nano /etc/fail2ban/filter.d/nginx-login.conf
```

```ini
[Definition]
failregex = ^<HOST> .* "POST .*/login.*" 401
ignoreregex =
```

### Добавить jail

```ini
[nginx-login]
enabled  = true
filter   = nginx-login
logpath  = /var/log/nginx/access.log
maxretry = 5
bantime  = 1h
findtime = 10m
```

> **Совет:** Для API с rate limiting это менее актуально.
> Но если есть форма логина — обязательно.

---

## 2.6 Свой IP в whitelist

> **Опасно:** Перед тестированием добавь свой IP в `ignoreip`.
> Иначе fail2ban заблокирует ТЕБЯ.

```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 203.0.113.50/32
```

`203.0.113.50` = твой IP.

---

## 📝 Упражнения

### Упражнение 2.1: Установить fail2ban
**Задача:**
1. Установи: `sudo apt install -y fail2ban`
2. Включи: `sudo systemctl enable --now fail2ban`
3. Проверь: `sudo fail2ban-client status`

### Упражнение 2.2: Настроить jail.local
**Задача:**
1. Создай `/etc/fail2ban/jail.local` (как в 2.3)
2. Добавь свой IP в `ignoreip`
3. Перезапусти: `sudo systemctl restart fail2ban`
4. Проверь: `sudo fail2ban-client status sshd`

### Упражнение 2.3: Симулировать атаку
**Задача:**
1. С ДРУГОГО IP (или виртуалки) сделай 3 неудачных SSH-попытки:
   ```bash
   ssh wronguser@server-ip  # неправильный пароль
   ```
2. На сервере проверь: `sudo fail2ban-client status sshd`
3. IP заблокирован? Сколько всего банов?
4. Разбань: `sudo fail2ban-client set sshd unbanip IP`

### Упражнение 2.4: Логи
**Задача:**
1. Посмотри логи fail2ban: `sudo journalctl -u fail2ban -n 20`
2. Видишь блокировки?
3. Посмотри сколько IP заблокировано: `sudo fail2ban-client banned`

### Упражнение 2.5: DevOps Think
**Задача:** «fail2ban заблокировал легитимного пользователя. Офис с одного IP, 10 сотрудников. Что делать?»

Ответ:
1. Добавь IP офиса в `ignoreip`
2. Или увеличь `maxretry` для sshd
3. Или увеличь `findtime` (реже банит)
4. Для офиса: используй SSH-ключи вместо паролей (тогда fail2ban не триггерится)

---

## 📋 Чеклист главы 2

- [ ] fail2ban установлен и запущен
- [ ] `jail.local` создан (не трогаю `jail.conf`)
- [ ] Мой IP в `ignoreip`
- [ ] sshd jail включён и работает
- [ ] nginx-http-auth jail включён
- [ ] Я могу посмотреть статус: `fail2ban-client status`
- [ ] Я могу разбанить IP: `fail2ban-client set sshd unbanip`
- [ ] Я могу посмотреть логи: `journalctl -u fail2ban`

**Всё отметил?** Переходи к Главе 3 — обновления.
