# Глава 6: Lynis в аудите

> **Цель:** использовать lynis как источник системных замечаний и динамики.

---

## 6.1 Запуск

```bash
sudo lynis audit system --report-file audits/2026-05-06/lynis.dat
```

Если директория недоступна для root или относительный путь неудобен, сохрани во временный файл и скопируй результат.

**Сохранение читаемого вывода для сравнения:**

```bash
sudo lynis audit system --quiet 2>&1 | tee audits/2026-05-06/lynis.txt
```

Флаг `--quiet` убирает детальный вывод каждого теста и оставляет только предупреждения и итог.

**Пример вывода с `--quiet`:**

```
# Пример вывода (только предупреждения и итог):

  [WARNING]: No firewall tool found. Make sure you have a firewall like
             iptables, nftables, or ufw configured and enabled.

  [WARNING]: Kernel version is not hardened with grsecurity/PaX.
             Suggestion: Apply a hardened kernel or use AppArmor.

  [WARNING]: Password hashing rounds for SHA512 are set too low (5000).
             Suggestion: Increase rounds to 65536 in /etc/pam.d/common-password.

  [WARNING]: SSH PermitRootLogin is set to "yes".
             Suggestion: Set "PermitRootLogin no" in /etc/ssh/sshd_config.

  [WARNING]: Found some temporary/development software on this system.
             Hint: gcc found in /usr/bin/gcc

  Hardening index : 58 [###########         ]
  Tests performed : 248
  Plugins enabled : 0

  Lynis 3.0.9
```

**Как читать вывод:**

- `[WARNING]` — предупреждение. Lynis считает это проблемой, но это не значит что сервер взломан.
- `Hardening index : 58` — набранные очки из 100. Отражает насколько система следует best practices. Это **динамический индикатор**, а не абсолютная мера безопасности.
- `Tests performed : 248` — сколько тестов выполнено.

---

## 6.2 Hardening index: динамика после исправлений

Hardening index показывает прогресс. Пример:

| Дата | Действие | Hardening Index |
|---|---|---|
| 2026-05-06 | первый аудит | 58 |
| 2026-05-06 | исправили SSH (PermitRootLogin no) | 62 |
| 2026-05-07 | включили ufw | 67 |
| 2026-05-07 | подняли rounds SHA512 в PAM | 71 |

Индекс 71 лучше чем 58 — это значит внедрили конкретные меры. Индекс 90+ требует специфических настроек (AppArmor, grsecurity) которые часто нецелесообразны на обычном VPS.

---

## 6.3 Сохранение результатов для сравнения

```bash
# Папка с датой
AUDIT_DIR="audits/$(date +%Y-%m-%d)"
mkdir -p "$AUDIT_DIR"

# Сохранить читаемый вывод
sudo lynis audit system --quiet 2>&1 | tee "$AUDIT_DIR/lynis.txt"

# Сохранить machine-readable отчёт
sudo lynis audit system --report-file "$AUDIT_DIR/lynis.dat"
```

Чтобы сравнить два прогона:

```bash
diff audits/2026-05-06/lynis.txt audits/2026-05-13/lynis.txt
```

Ищи: исчезли ли WARNING которые ты исправлял? Появились ли новые?

---

## 6.4 Топ-3 suggestion которые быстрее всего поднимают индекс

**1. SSH: PermitRootLogin no**

Lynis часто находит включённый root login в SSH. Исправление простое:

```bash
grep PermitRootLogin /etc/ssh/sshd_config
# Если: PermitRootLogin yes — меняем:
sudo sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

Даёт +3-5 к hardening index.

**2. Firewall: включить ufw**

```bash
sudo apt install ufw -y
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

Lynis перестанет предупреждать об отсутствии firewall. Даёт +5-8 к индексу.

**3. Обновление пакетов**

```bash
sudo apt update && sudo apt upgrade -y
```

Lynis проверяет наличие обновлений. После установки перезапусти lynis — предупреждение об outdated packages исчезнет.

---

## 6.5 Что важно

- firewall;
- SSH;
- updates;
- users;
- malware scanners только если уместно;
- hardening index как динамика, а не абсолютная цель.

---

## 6.6 Backlog

Сделай список suggestions:

| ID | Тема | Нужно? | Почему | Действие |
|---|---|---|---|---|

Не все suggestions надо выполнять. Некоторые не нужны для VPS без физического доступа. Например, suggestion о шифровании жёсткого диска (LUKS) нерелевантен для облачного VPS — ты не контролируешь физический диск.

---

## 6.7 Практика

Выбери три предупреждения lynis и объясни их человеческим языком. Проверка: по каждому есть решение — исправить, отложить или принять риск.
