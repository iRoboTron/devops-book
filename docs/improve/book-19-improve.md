# Инструкция агенту: улучшение книги 19 «Detection, Monitoring, Incident Response»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/19-incident-response-devops/
```

Книга: 1233 строки. Одна из лучших в части 3 — глава 1 (логи) написана отлично. Главные проблемы:
1. В нескольких практических разделах вместо реальных команд стоят **заглушки** `printf 'review backup permissions\n'` — это нужно заменить на настоящие команды
2. Глава 6 (Ransomware) — раздел 6.2 перечисляет признаки без команды их обнаружения
3. Глава 9 (Итоговый проект) — нет команд для симуляции инцидента на своём стенде

---

## Замена всех заглушек `printf`

Во всех главах найти и заменить конструкции вида:
```bash
printf 'review backup permissions\n'
printf 'credential\nowner\n...\n'
```

Это заглушки — они не делают ничего полезного. Каждую заменить реальной командой, релевантной контексту раздела.

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — Логи как сырьё

**Глава хорошая.** Добавить одну вещь — проверка что логи не содержат чувствительные данные:

**Добавить** в раздел 1.4 Шаг 3 реальную команду поиска утечек в логах:

```bash
# Поиск токенов и паролей в логах приложения
sudo journalctl -u myapp --no-pager | \
  grep -iE "token=|password=|secret=|Authorization: Bearer|api_key=" | \
  head -20

# Поиск в файловых логах
sudo grep -rE "password|token|secret|bearer" /var/log/nginx/ 2>/dev/null | head -10
```

Если что-то нашлось — это утечка. Нужно:
1. Исправить приложение (не логировать чувствительное)
2. Rotate скомпрометированные ключи
3. Удалить или ограничить доступ к старым логам

---

### Глава 3 (`chapter-03.md`) — Host-level detection

**Проблема:** Раздел 3.4 описывает snapshot baseline, но нет команды сравнить текущее состояние с baseline.

**Добавить** раздел **3.5 «Сравнить текущее состояние с baseline»:**

```bash
# Сохранить baseline слушающих портов
ss -tulpn > /tmp/baseline-ports.txt

# Через некоторое время — сравнить
ss -tulpn > /tmp/current-ports.txt
diff /tmp/baseline-ports.txt /tmp/current-ports.txt
```

Новые строки в diff — появились новые сервисы. Нужно разобраться: это expected изменение или аномалия.

**Добавить** простой file integrity check для критичных файлов:

```bash
# Сохранить хеши критичных файлов
sha256sum /etc/passwd /etc/shadow /etc/sudoers /etc/ssh/sshd_config > /var/log/integrity-baseline.txt

# Проверить позже
sha256sum -c /var/log/integrity-baseline.txt
```

```
/etc/passwd: OK
/etc/shadow: OK
/etc/sudoers: FAILED    ← файл изменён
/etc/ssh/sshd_config: OK
```

`FAILED` = файл изменён после создания baseline. Нужно выяснить кто и когда изменил:

```bash
sudo stat /etc/sudoers
sudo journalctl --since "2 hours ago" | grep sudoers
```

---

### Глава 6 (`chapter-06.md`) — Ransomware resilience

**Проблема 1:** Раздел 6.4 Шаг 1 содержит заглушку:
```bash
printf 'review backup permissions and storage path\n'
```

**Заменить** на реальные команды проверки backup isolation:

```bash
# Проверить права на директорию с бэкапами
ls -la /var/backups/
# Должно быть: owner=root, права 700 или 750 — только root/backup-user пишет

# Проверить может ли app-пользователь удалить бэкап
sudo -u appuser rm /var/backups/db-backup-latest.sql 2>&1
# Ожидаемо: Permission denied

# Проверить рабочий скрипт бэкапа
cat /etc/cron.d/backup
# Посмотреть от кого запускается и куда пишет
```

Если app-пользователь может удалить бэкап — при компрометации приложения бэкапы тоже потеряны. Исправить: chmod 700 + chown root на директорию бэкапов.

**Проблема 2:** Раздел 6.2 «Типовые слабые места» — «массовые file changes не мониторятся» — не показано как мониторить.

**Добавить** в раздел 6.4 Шаг по мониторингу аномальных file changes:

```bash
# Установить inotify-tools
sudo apt install inotify-tools

# Наблюдать за критичными директориями (lab-only)
inotifywait -m -r /var/www/myapp -e modify,delete,create,move 2>&1 | \
  awk '{print strftime("[%Y-%m-%d %H:%M:%S]"), $0}' | \
  tee /var/log/file-changes.log
```

```
[2026-04-25 03:15:01] /var/www/myapp/ MODIFY config.py
[2026-04-25 03:15:02] /var/www/myapp/ MODIFY config.py.bak
[2026-04-25 03:15:03] /var/www/myapp/ CREATE new-file-000001.enc
[2026-04-25 03:15:03] /var/www/myapp/ CREATE new-file-000002.enc  ← массовое создание .enc = признак шифрования
```

Для production: использовать auditd:

```bash
# Следить за изменениями в /etc
sudo auditctl -w /etc/passwd -p wa -k passwd_changes
sudo auditctl -w /var/www -p wax -k webroot_changes

# Смотреть события
sudo ausearch -k passwd_changes --start today
```

---

### Глава 7 (`chapter-07.md`) — Triage и containment

**Добавить** в практику команды быстрой изоляции хоста:

```bash
# Быстрая изоляция: заблокировать весь входящий и исходящий трафик
# (кроме SSH с твоего IP — иначе потеряешь управление)
sudo ufw default deny incoming
sudo ufw default deny outgoing
sudo ufw allow from YOUR_ADMIN_IP to any port 22
sudo ufw enable

# Более жёсткая изоляция через iptables (если ufw недоступен)
sudo iptables -P INPUT DROP
sudo iptables -P OUTPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -A INPUT -s YOUR_ADMIN_IP -j ACCEPT
sudo iptables -A OUTPUT -d YOUR_ADMIN_IP -j ACCEPT
```

**ВАЖНО:** Всегда сначала разрешить свой IP — иначе потеряешь SSH-доступ.

---

### Глава 9 (`chapter-09.md`) — Итоговый проект

**Проблема:** Нет команд для симуляции инцидента на своём стенде.

**Добавить** в раздел 9.3 конкретные lab-only симуляции для каждой фазы:

**Симуляция: подозрительный процесс**

```bash
# Запустить на своей lab-машине «подозрительный» процесс
# (nc в режиме прослушивания на нестандартном порту)
nc -l -p 4444 &

# Обнаружить его
ss -tulpn | grep 4444
# LISTEN 0 1 0.0.0.0:4444 users:(("nc",pid=12345,...))

sudo lsof -i :4444
# nc  12345 user  3u  IPv4  ... TCP *:4444 (LISTEN)
```

**Симуляция: аномальный burst login**

```bash
# На второй машине в lab создать несколько неудачных SSH-попыток
for i in {1..5}; do
  ssh wronguser@TARGET_IP -o ConnectTimeout=3 2>/dev/null || true
done

# На target найти события
sudo grep "Failed password\|Invalid user" /var/log/auth.log | tail -10
# или
sudo journalctl -u ssh -n 20 --no-pager | grep "Failed\|Invalid"
```

**Симуляция: изменение критичного файла**

```bash
# Добавить строку в /etc/crontab (на своей lab)
echo "# test entry" | sudo tee -a /etc/crontab

# Обнаружить через audit или diff с baseline
sudo sha256sum -c /var/log/integrity-baseline.txt 2>/dev/null | grep FAILED
```

---

## Приоритет

1. Заменить все `printf`-заглушки реальными командами (глава 6, возможно другие)
2. Глава 6 (Ransomware) — реальные команды проверки backup isolation и inotifywait
3. Глава 9 (Проект) — добавить lab симуляции инцидентов
4. Глава 3 — сравнение с baseline через diff и sha256sum

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-19-improve.md`*
