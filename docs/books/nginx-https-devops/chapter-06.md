# Глава 6: Фаервол с ufw

> **Запомни:** Без фаервола твой сервер — дом с открытыми дверями. Любой может постучаться в любой порт. Фаервол — это замок на двери.

---

## 6.1 Зачем нужен фаервол

Представь: ты настроил Nginx, HTTPS, Python-приложение. Всё работает.

Но на сервере также работает:
- PostgreSQL на порту 5432
- Redis на порту 6379
- SSH на порту 22
- Может быть Docker с кучей портов

**Без фаервола:**
```
Интернет
  ├──→ 22   (SSH)       ← Любой может попробовать подобрать пароль
  ├──→ 80   (HTTP)      ← Это ок
  ├──→ 443  (HTTPS)     ← Это ок
  ├──→ 5432 (PostgreSQL) ← КАТАСТРОФА! Данные без защиты
  ├──→ 6379 (Redis)      ← КАТАСТРОФА! Полный доступ к кешу
  └──→ 8080 (что-то ещё) ← Может быть что угодно
```

**С фаерволом:**
```
Интернет
  ├──→ 22   (SSH)       ← Разрешено
  ├──→ 80   (HTTP)      ← Разрешено
  ├──→ 443  (HTTPS)     ← Разрешено
  ├──→ 5432 (PostgreSQL) ← ЗАБЛОКИРОВАНО
  ├──→ 6379 (Redis)      ← ЗАБЛОКИРОВАНО
  └──→ 8080 (что-то ещё) ← ЗАБЛОКИРОВАНО
```

> **Запомни:** Принцип минимальных привилегий.
> Открывай только то что нужно. Всё остальное — закрыто.

---

## 6.2 Что такое ufw

**ufw** (Uncomplicated Firewall) — простая обёртка над `iptables`.

```
Ты → ufw (простые команды) → iptables (сложные правила ядра)
```

Без ufw ты бы писал:
```bash
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -P INPUT DROP
```

С ufw:
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw enable
```

> **Совет:** ufw — для 95% задач.
> iptables — когда нужна тонкая настройка (редко).

---

## 6.3 Проверка статуса

```bash
sudo ufw status
Status: inactive
```

`inactive` — фаервол выключен. Все порты открыты.

```bash
sudo ufw status verbose
Status: inactive
```

`verbose` = подробно. Когда включён — покажет все правила.

---

## 6.4 Базовые настройки по умолчанию

### Политика по умолчанию

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

| Правило | Что значит |
|---------|-----------|
| `deny incoming` | Все входящие — заблокированы (если нет разрешающего правила) |
| `allow outgoing` | Все исходящие — разрешены |

> **Запомни:** Это база. Всё что не разрешил явно — заблокировано.
> Установи это **перед** тем как включать ufw.

---

## 6.5 Разрешить порт

### По номеру порта

```bash
sudo ufw allow 22     # SSH
sudo ufw allow 80     # HTTP
sudo ufw allow 443    # HTTPS
```

### По имени сервиса

```bash
sudo ufw allow ssh    # То же что allow 22
sudo ufw allow http   # То же что allow 80
```

Имена берутся из `/etc/services`.

### TCP или UDP

```bash
sudo ufw allow 22/tcp    # Только TCP
sudo ufw allow 53/udp    # Только UDP
```

Без указания протокола — разрешает оба.

---

## 6.6 Разрешить для конкретной сети

```bash
sudo ufw allow from 10.0.0.0/8 to any port 5432
```

Порт 5432 (PostgreSQL) доступен только из сети `10.0.0.0/8`.

```bash
sudo ufw allow from 192.168.1.0/24 to any port 22
```

SSH только из локальной сети `192.168.1.0/24`.

> **Запомни:** Это как ты делаешь когда хочешь чтобы
> база данных была доступна только из внутренней сети.

---

## 6.7 Профили приложений

Некоторые пакеты создают профили для ufw.

```bash
sudo ufw app list
Available applications:
  Nginx Full
  Nginx HTTP
  Nginx HTTPS
  OpenSSH
```

### Что в профиле

```bash
sudo ufw app info 'Nginx Full'
Profile: Nginx Full
Title: Web Server (Nginx, HTTP + HTTPS)
Description: Small, but very powerful and efficient web server
Ports:
  80,443/tcp
```

### Использовать профиль

```bash
sudo ufw allow 'Nginx Full'    # Порты 80 и 443
sudo ufw allow 'Nginx HTTP'    # Только порт 80
sudo ufw allow 'Nginx HTTPS'   # Только порт 443
sudo ufw allow OpenSSH         # Порт 22
```

> **Совет:** Профили удобнее чем запоминать порты.
> Но для нестандартных портов (8000, 3000) — используй номер.

---

## 6.8 Удалить правило

### Посмотреть правила с номерами

```bash
sudo ufw status numbered
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 80/tcp                     ALLOW IN    Anywhere
[ 3] 443/tcp                    ALLOW IN    Anywhere
[ 4] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
[ 5] 80/tcp (v6)                ALLOW IN    Anywhere (v6)
[ 6] 443/tcp (v6)               ALLOW IN    Anywhere (v6)
```

### Удалить по номеру

```bash
sudo ufw delete 3
```

Удалит правило номер 3 (443/tcp).

### Удалить по описанию

```bash
sudo ufw delete allow 80
```

---

## 6.9 Включить и выключить

### Включить

```bash
sudo ufw enable
```

> **Опасно:** Перед `ufw enable` убедись что:
> 1. ✅ `ufw allow 22` добавлено (не потеряешь SSH)
> 2. ✅ `ufw status` показывает правильные правила
> 3. ✅ Ты подключён по SSH и можешь зайти через консоль если что

### Выключить

```bash
sudo ufw disable
```

Все правила сохранятся. Просто не применяются.

### Перезагрузить правила

```bash
sudo ufw reload
```

---

## 6.10 Логирование

```bash
sudo ufw logging on
```

Заблокированные подключения пишутся в лог:

```bash
tail -f /var/log/ufw.log
Apr  9 14:30:00 server kernel: [UFW BLOCK] IN=eth0 SRC=203.0.113.50 DST=10.0.0.1 ...
```

### Уровни логирования

```bash
sudo ufw logging low      # Только заблокированные
sudo ufw logging medium   # Стандартный
sudo ufw logging high     # Подробный
sudo ufw logging full     # Очень подробный (много данных!)
```

> **Совет:** `logging on` — включи. Полезно видеть кто ломится в закрытые порты.
> `logging full` — не используй, завалит диск логами.

---

## 6.11 Порядок правил — почему важен

ufw применяет правила **сверху вниз**. Первое совпадение — побеждает.

```bash
sudo ufw allow from 10.0.0.0/8 to any port 5432   # Правило 1
sudo ufw deny 5432                                  # Правило 2
```

Запрос из `10.0.0.5`:
- Правило 1: `10.0.0.5` в `10.0.0.0/8`? ✅ → разрешено
- Дальше не проверяет

Запрос из `203.0.113.50`:
- Правило 1: `203.0.113.50` в `10.0.0.0/8`? ❌ → дальше
- Правило 2: deny 5432? ✅ → заблокировано

> **Запомни:** Специфичные правила — вверх. Общие — вниз.
> Если сначала deny all — остальные правила не сработают.

---

## 6.12 Типичная настройка для веб-сервера

Вот готовый набор правил:

```bash
# 1. Политика по умолчанию
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. Разрешить SSH (ОБЯЗАТЕЛЬНО перед enable!)
sudo ufw allow OpenSSH

# 3. Разрешить веб
sudo ufw allow 'Nginx Full'
# или:
# sudo ufw allow 80
# sudo ufw allow 443

# 4. (Опционально) Доступ к БД только из внутренней сети
# sudo ufw allow from 10.0.0.0/8 to any port 5432

# 5. Включить
sudo ufw enable

# 6. Проверить
sudo ufw status verbose
```

### Результат

```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing)

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
```

---

## 📝 Упражнения

### Упражнение 6.1: Базовая настройка
**Задача:** Настрой фаервол для типичного веб-сервера.
1. Посмотри статус: `sudo ufw status`
2. Установи политику: `sudo ufw default deny incoming`
3. Разреши SSH: `sudo ufw allow OpenSSH`
4. Разреши HTTP/HTTPS: `sudo ufw allow 'Nginx Full'`
5. Проверь правила: `sudo ufw status numbered`
6. Включи: `sudo ufw enable`
7. Проверь: `sudo ufw status verbose`

### Упражнение 6.2: Проверка закрытых портов
**Задача:** Убедись что лишние порты закрыты.
1. С другого терминала (или с хост-машины):
   ```bash
   nc -zv IP-сервера 22
   nc -zv IP-сервера 80
   nc -zv IP-сервера 443
   ```
2. Попробуй закрытый порт:
   ```bash
   nc -zv IP-сервера 5432
   ```
3. Что отвечает? (`Connection refused` или `Connection timed out`?)

### Упражнение 6.3: Удаление и добавление правил
**Задача:**
1. Добавь правило для кастомного порта: `sudo ufw allow 8000`
2. Проверь: `sudo ufw status numbered`
3. Удали его по номеру: `sudo ufw delete N`
4. Убедись что удалён

### Упражнение 6.4: Ограничение по сети
**Задача:**
1. Разреши SSH только из определённой сети:
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 22
   ```
2. Проверь: `sudo ufw status verbose`
3. (Опасно!) Если ты в другой сети — НЕ включай это на реальном сервере.
   На виртуалке — безопасно.

### Упражнение 6.5: DevOps Think
**Задача:** «Ты включил ufw и сразу потерял SSH-подключение. Как восстановиться? Что делать?»

Ответ:
1. Если виртуалка — открой консоль VirtualBox (не SSH)
2. Если VPS — войди через веб-консоль провайдера
3. Выключи ufw: `sudo ufw disable`
4. Добавь правило: `sudo ufw allow 22`
5. Включи снова: `sudo ufw enable`
6. Урок: всегда `ufw allow 22` **до** `ufw enable`

---

## 📋 Чеклист главы 6

- [ ] Я понимаю зачем нужен фаервол
- [ ] Я понимаю что ufw — обёртка над iptables
- [ ] Я могу посмотреть статус (`ufw status`)
- [ ] Я могу установить политику по умолчанию
- [ ] Я могу разрешить порт (`ufw allow`)
- [ ] Я могу разрешить для конкретной сети (`ufw allow from ...`)
- [ ] Я могу использовать профили (`ufw app list`)
- [ ] Я могу удалить правило (`ufw delete`)
- [ ] Я понимаю важность порядка правил
- [ ] Я знаю что нужно `ufw allow 22` **перед** `ufw enable`
- [ ] Я могу настроить типичный веб-сервер

**Всё отметил?** Переходи к Главе 7 — диагностика сетевых проблем.
