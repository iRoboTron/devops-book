# Глава 4: Минимизация поверхности атаки

> **Запомни:** Меньше запущено → меньше уязвимостей → меньше что ломать. Каждый лишний сервис — потенциальная дыра.

---

## 4.1 Аудит запущенных сервисов

### Что работает

```bash
systemctl list-units --type=service --state=running
```

Покажет все активные сервисы.

### Что слушает порты

```bash
ss -tlnp
State   Recv-Q  Send-Q   Local Address:Port    Process
LISTEN  0       128      0.0.0.0:22            sshd
LISTEN  0       511      0.0.0.0:80            nginx
LISTEN  0       511      0.0.0.0:443           nginx
```

Только SSH, Nginx (80/443). Правильно.

Если видишь что-то неожиданное — разбирайся.

---

## 4.2 Отключить ненужные сервисы

### Типичные кандидаты

```bash
# Bluetooth (на сервере не нужен)
sudo systemctl disable --now bluetooth

# CUPS (принтеры)
sudo systemctl disable --now cups

# ModemManager
sudo systemctl disable --now ModemManager

# Avahi (mDNS)
sudo systemctl disable --now avahi-daemon
```

### Проверить

```bash
ss -tlnp
# Стало меньше сервисов?
```

> **Совет:** Перед отключением узнай что делает сервис.
> `systemctl status servicename` покажет описание.

---

## 4.3 Аудит открытых портов

### Локально

```bash
ss -tlnp
```

### Полное сканирование (с внешней машины)

```bash
nmap -sV server-ip
```

Покажет:
- Какие порты открыты НАРУЖУ
- Какие сервисы за ними
- Версии сервисов

### Результат должен быть

```
PORT    STATE  SERVICE
22/tcp  open   ssh
80/tcp  open   http
443/tcp open   https
```

Если видишь что-то ещё — разбирайся.

---

## 4.4 Аудит пользователей

### Кто может войти

```bash
getent passwd | grep -v nologin | grep -v false
```

Покажет пользователей с оболочкой.

### У кого sudo

```bash
getent group sudo
sudo:x:27:deploy
```

Только `deploy`? Правильно.

### Удалить неиспользуемых

```bash
# Посмотри кто есть
cat /etc/passwd | grep -v nologin | grep -v false

# Удали лишнего
sudo userdel -r olduser
```

---

## 4.5 SUID/SGID файлы

Файлы с SUID запускаются от владельца (часто root), а не от того кто запустил.

### Найти SUID файлы

```bash
find / -perm /4000 -type f 2>/dev/null
```

Нормальные SUID файлы:

```
/usr/bin/passwd      ← смена пароля
/usr/bin/sudo        ← sudo
/usr/bin/su          ← смена пользователя
```

Подозрительные — гугли.

---

## 4.6 lynis — автоматический аудит

`lynis` сканирует систему и даёт рекомендации.

### Установка

```bash
sudo apt install -y lynis
```

### Запуск

```bash
sudo lynis audit system
```

### Результат

```
[+] System Information
  - OS: Ubuntu 24.04
  - Kernel: 6.8.0
  - ...

[+] Hardening Index: 72/100

[+] Suggestions:
  - [HRDN-7231] Disable root login via SSH (done)
  - [NETW-2705] Configure firewall (done)
  - [FILE-6344] Set password on GRUB
  - [BOOT-5122] Enable UEFI secure boot
  ...
```

### Hardening Index

| Score | Значение |
|-------|----------|
| < 50 | Слабая защита |
| 50-70 | Средняя |
| 70-85 | Хорошая |
| > 85 | Отличная |

> **Совет:** Запускай lynis раз в месяц.
> Применяй рекомендации с высоким приоритетом.

---

## 📝 Упражнения

### Упражнение 4.1: Аудит сервисов
**Задача:**
1. Посмотри запущенные сервисы: `systemctl list-units --type=service --state=running`
2. Посмотри порты: `ss -tlnp`
3. Есть ли что-то неожиданное?

### Упражнение 4.2: Отключить лишнее
**Задача:**
1. Найди ненужные сервисы
2. Отключи: `sudo systemctl disable --now servicename`
3. Проверь: `ss -tlnp` — стало чище?

### Упражнение 4.3: Пользователи
**Задача:**
1. Посмотри кто может войти: `getent passwd | grep -v nologin`
2. Посмотри sudo: `getent group sudo`
3. Всё правильно?

### Упражнение 4.4: lynis
**Задача:**
1. Установи: `sudo apt install -y lynis`
2. Запусти: `sudo lynis audit system`
3. Какой Hardening Index?
4. Какие топ-5 рекомендаций?
5. Примени те что понятны

### Упражнение 4.5: DevOps Think
**Задача:** «nmap показал открытый порт 3306 (MySQL) на сервере где только PostgreSQL. Что это значит и что делать?»

Ответ:
1. Кто-то установил MySQL (или это было по умолчанию)
2. Если не используется — останови и удали: `sudo systemctl stop mysql && sudo apt remove mysql-server`
3. Если используется — закрой фаерволом: `sudo ufw deny 3306`
4. Узнай кто поставил и зачем

---

## 📋 Чеклист главы 4

- [ ] Я знаю какие сервисы запущены
- [ ] Я знаю какие порты открыты
- [ ] Отключил ненужные сервисы
- [ ] Проверил пользователей (только нужные с sudo)
- [ ] Знаю как найти SUID файлы
- [ ] Запустил lynis и применил рекомендации
- [ ] Hardening Index > 70

**Всё отметил?** Часть 1 (Безопасность) завершена. Переходи к Главе 5 — Netdata.
