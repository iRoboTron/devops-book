# Глава 6: Логи и fail2ban

> **Цель:** видеть попытки входа и автоматически банить грубый перебор.

---

## 6.1 Логи SSH

```bash
journalctl -u ssh --since "1 hour ago"
grep "Failed password\|Invalid user" /var/log/auth.log | tail -20
```

# Пример вывода:
```
May  5 03:11:42 myserver sshd[9821]: Failed password for invalid user admin from 45.33.32.156 port 52341 ssh2
May  5 03:11:43 myserver sshd[9822]: Failed password for invalid user root from 45.33.32.156 port 52342 ssh2
May  5 03:11:44 myserver sshd[9823]: Failed password for invalid user ubuntu from 45.33.32.156 port 52343 ssh2
May  5 03:11:46 myserver sshd[9824]: Failed password for invalid user pi from 185.234.218.5 port 41209 ssh2
May  5 03:12:01 myserver sshd[9831]: Failed password for deploy from 45.33.32.156 port 52360 ssh2
```

Это нормальная картина для любого VPS с открытым SSH. Разные IP, разные имена пользователей — это автоматические боты, не целевая атака.

```bash
grep "Accepted" /var/log/auth.log | tail -10
```

# Пример вывода:
```
May  5 14:15:02 myserver sshd[12001]: Accepted publickey for deploy from 93.184.216.34 port 54321 ssh2: RSA SHA256:abc...
```

`Accepted publickey` — успешный вход по ключу. Только эти строки должны быть в логе при правильной настройке.

На некоторых системах имя сервиса или путь лога отличаются. Если команды пустые, проверь `journalctl`.

---

## 6.2 fail2ban

> **Аналогия:** fail2ban — это охранник, который видит: «этот IP пытался войти 5 раз за 10 минут и провалился» — и вносит его в чёрный список на час. Боты идут дальше, а сервер отдыхает.

```bash
sudo apt install fail2ban
```

`/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port = 22
maxretry = 5
findtime = 600
bantime = 3600
```

Проверка:

```bash
sudo systemctl status fail2ban
sudo fail2ban-client status sshd
```

# Пример вывода `fail2ban-client status sshd`:
```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 3
|  |- Total failed:     247
|  `- Journal matches:  _SYSTEMD_UNIT=sshd.service + _COMM=sshd
`- Actions
   |- Currently banned: 2
   |- Total banned:     18
   `- Banned IP list:   45.33.32.156 185.234.218.5
```

`Currently banned: 2` — прямо сейчас заблокированы 2 IP. `Total failed: 247` — столько неудачных попыток за время работы jail.

```bash
sudo fail2ban-client banned
```

# Пример вывода:
```
[{'sshd': ['45.33.32.156', '185.234.218.5']}]
```

---

## 6.3 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** Заблокировал сам себя — ssh выдаёт `Connection refused` или не отвечает с твоего IP.
>
> **Шаги исправления:**
>
> **Вариант 1 — если ещё есть другой открытый SSH-сеанс:**
> ```bash
> sudo fail2ban-client unban ВАШ_IP
> ```
> Например: `sudo fail2ban-client unban 93.184.216.34`
>
> **Вариант 2 — через консоль провайдера:**
> 1. Войди через VNC/KVM в панели провайдера.
> 2. Выполни: `sudo fail2ban-client unban ВАШ_IP`
> 3. Или временно останови fail2ban: `sudo systemctl stop fail2ban` (потом запусти снова).
>
> **Чтобы не повторялось:** добавь свой IP в белый список в `/etc/fail2ban/jail.local`:
> ```ini
> [DEFAULT]
> ignoreip = 127.0.0.1/8 ::1 93.184.216.34
> ```
>
> **Симптом:** fail2ban не банит — `Currently banned: 0` хотя в логах много Failed password.
>
> Проверь: порт SSH в jail.local совпадает с реальным (`port = 22`); имя лога или unit правильное (`backend = systemd` или `logpath = /var/log/auth.log`).

---

## 6.4 Не полагаться только на fail2ban

fail2ban снижает шум, но не заменяет SSH-ключи и запрет паролей. Если парольный вход включён, fail2ban — это пластырь, а не решение.

---

## 6.5 Практика

Настрой fail2ban и проверь статус jail. Запиши, какой порт SSH используется. Если ты менял порт SSH, не забудь поменять его в fail2ban.
