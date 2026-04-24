# Инструкция агенту: улучшение книги 20 «Attacker Mindset для защитника»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/20-attacker-mindset-devops/
```

Книга: 1182 строки. Самая «списочная» из всех книг части 3. Почти каждый раздел 3.2 «Как выглядит риск» — чистый перечень без механики. Дополнительно: **в нескольких практических разделах стоят заглушки** `printf '...\n'` вместо реальных команд.

**Важное ограничение книги:** все offensive-примеры — только lab-only, только на своих системах, без реального эксплойта. Задача книги — помочь защитнику думать как атакующий, а не научить атаковать. Этот принцип нужно сохранить.

---

## Общий принцип исправления

Каждый пункт «Типовые слабые места» нужно превратить в цикл:
1. **Механика** — как атака работает в общих чертах (без реального PoC)
2. **Признак** — что видно в логах/трафике/системе
3. **Команда проверки** — как обнаружить у себя

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — Reconnaissance

**Добавить** в раздел 1.4 проверку что наружу не торчит лишнего (defensive reconnaissance своего сервера):

```bash
# Что видит сканер на твоём сервере
nmap -Pn -sV --version-intensity 2 SERVER_IP

# Что видно в HTTP-заголовках
curl -sI https://SERVER_IP | grep -E "Server:|X-Powered-By:|Via:"
# Ожидаемо: Server: nginx (без версии), нет X-Powered-By
# Плохо:    Server: nginx/1.14.2 — версия раскрыта
```

**Добавить** раздел **1.5 «Что раскрывает DNS — проверить самому»:**

```bash
# Проверить свои публичные записи
dig +short A yourdomain.com
dig +short MX yourdomain.com
dig +short TXT yourdomain.com   # часто содержит служебные данные
dig +short NS yourdomain.com

# Поиск поддоменов через Certificate Transparency (пассивная разведка)
curl -s "https://crt.sh/?q=%.yourdomain.com&output=json" | \
  jq -r '.[].name_value' | sort -u | head -30
```

Если видишь поддомены которые не должны быть публичными (`admin.`, `internal.`, `vpn.`) — это reconnaissance-поверхность.

---

### Глава 2 (`chapter-02.md`) — Initial access vectors

**Добавить** в практику проверку что admin-панели не торчат наружу:

```bash
# Проверить типичные admin-пути на своём сервере
for path in /admin /wp-admin /phpmyadmin /.env /config.php /_cpanel; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://SERVER_IP$path")
  echo "$code $path"
done
```

```
404 /admin
404 /wp-admin
200 /.env   ← ПРОБЛЕМА: файл конфига доступен
404 /phpmyadmin
```

---

### Глава 3 (`chapter-03.md`) — Credential abuse

**Проблема 1:** Раздел 3.4 Шаг 1 содержит заглушку:
```bash
printf 'credential\nowner\nlocation\nrotation\n'
```

**Заменить** на реальную инвентаризацию credentials:

```bash
# SSH ключи в системе
find /home -name "authorized_keys" 2>/dev/null | xargs -I{} sh -c 'echo "=== {} ==="; cat {}'

# Сколько ключей у каждого пользователя
for user in $(cut -d: -f1 /etc/passwd); do
  home=$(getent passwd $user | cut -d: -f6)
  if [ -f "$home/.ssh/authorized_keys" ]; then
    count=$(grep -c "ssh-" "$home/.ssh/authorized_keys" 2>/dev/null || echo 0)
    echo "$user: $count ключей"
  fi
done

# Кто имеет доступ к sudo
getent group sudo | cut -d: -f4
cat /etc/sudoers | grep -v "^#" | grep -v "^$"

# Последние успешные и неудачные логины
last -a | head -20
lastb | head -20  # неудачные попытки (требует sudo)
```

**Добавить** в раздел 3.2 механику credential abuse:

**Shared admin accounts** — когда несколько человек используют один логин (`admin`, `ubuntu`), при инциденте невозможно определить кто именно действовал и когда. В логах все события выглядят одинаково.

Проверить:
```bash
# Сколько публичных ключей в authorized_keys у admin/ubuntu/root
cat /root/.ssh/authorized_keys 2>/dev/null | wc -l
# Больше 1 = shared access, нет разделения ответственности
```

**Long-lived API keys** — ключи которые никогда не ротировались остаются действительными даже после ухода сотрудника или утечки:

```bash
# Найти .env файлы в системе
find /opt /home /var -name ".env" 2>/dev/null
# Для каждого: посмотреть возраст
stat /opt/myapp/.env | grep Modify
```

---

### Глава 4 (`chapter-04.md`) — Уязвимые компоненты

**Добавить** в практику конкретный audit зависимостей:

```bash
# Python
pip-audit 2>/dev/null || pip install pip-audit && pip-audit

# Node.js
npm audit --production 2>/dev/null | head -30

# Docker образ
trivy image --severity HIGH,CRITICAL myapp:latest 2>/dev/null | head -40

# Установленные пакеты на хосте
# Debian/Ubuntu: найти пакеты с known CVE
sudo apt list --upgradable 2>/dev/null | grep -i "security" | head -20
```

---

### Глава 5 (`chapter-05.md`) — Защита приложения

**Добавить** lab-only проверку что приложение не раскрывает лишнее в заголовках:

```bash
# Полный набор заголовков ответа
curl -sI https://SERVER_IP

# Что должно быть:
# X-Frame-Options: SAMEORIGIN
# X-Content-Type-Options: nosniff
# Referrer-Policy: strict-origin-when-cross-origin
# Strict-Transport-Security: max-age=31536000

# Чего не должно быть:
# X-Powered-By: PHP/7.4.3   ← раскрывает версию
# Server: Apache/2.4.41     ← раскрывает версию
```

---

### Глава 6 (`chapter-06.md`) — Lateral movement

**Добавить** раздел **6.5 «Построить карту SSH-доверия»:**

```bash
# Посмотреть known_hosts — к каким серверам ты уже подключался
cat ~/.ssh/known_hosts | awk '{print $1}' | sort -u

# Посмотреть .ssh/config — к каким серверам настроены алиасы
cat ~/.ssh/config 2>/dev/null

# Проверить нет ли одного ключа на всех серверах
# Сравнить fingerprints публичных ключей
for key in ~/.ssh/id_*pub 2>/dev/null; do
  echo "=== $key ==="; ssh-keygen -lf "$key"; done
```

Если один и тот же ключ используется для всех серверов — компрометация одного = доступ ко всем.

**Добавить** в раздел 6.2 механику lateral movement:

**Shared SSH keys** — один приватный ключ открывает доступ ко всем серверам где добавлен соответствующий публичный. Атакующий находит один файл `id_rsa` и получает доступ ко всей инфраструктуре.

Проверить:
```bash
# Проверить что каждый сервер имеет уникальный authorized_keys
# (не одни и те же публичные ключи везде)
ssh server1 "cat ~/.ssh/authorized_keys" | sort > /tmp/keys-server1.txt
ssh server2 "cat ~/.ssh/authorized_keys" | sort > /tmp/keys-server2.txt
diff /tmp/keys-server1.txt /tmp/keys-server2.txt
# Нет diff = одинаковые ключи = одна точка отказа
```

---

### Глава 9 (`chapter-09.md`) — Итоговый проект

**Добавить** в раздел 9.3 конкретные lab-only defensive recon задания:

```bash
# Задание 1: Reconnaissance своего сервера
# Запустить с отдельной машины в lab:
nmap -Pn -sV --version-intensity 2 TARGET_IP 2>/dev/null

# Зафиксировать: что видит внешний наблюдатель?
# Цель: только 22, 80, 443 — ничего лишнего

# Задание 2: Credential audit
find /home -name "authorized_keys" 2>/dev/null | \
  xargs -I{} sh -c 'echo "=== {} ==="; wc -l < {}'
# Цель: у каждого пользователя свои ключи, не shared

# Задание 3: Lateral movement check
# Убедиться что серверы имеют разные ключи
# Убедиться что с compromised app-server нельзя попасть на db-server
ssh -i /opt/myapp/.ssh/app_key db-server 2>&1
# Ожидаемо: Permission denied
```

---

## Приоритет

1. Глава 3 (Credentials) — заменить заглушку `printf` реальной инвентаризацией
2. Глава 6 (Lateral movement) — карта SSH-доверия и механика shared keys
3. Глава 1 (Recon) — defensive recon своего сервера (curl заголовки, crt.sh)
4. Все главы — трансформировать «Типовые слабые места» из списков в объяснения с командами

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-20-improve.md`*
