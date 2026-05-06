# Глава 7: Lynis как контроль

> **Цель:** использовать lynis не как "магический рейтинг", а как список подсказок.

---

## 7.1 Установка и запуск

```bash
sudo apt install lynis
sudo lynis audit system
```

> **Аналогия:** Lynis — это как технический осмотр автомобиля. Механик не говорит «машина плохая» — он даёт список: «замени масло, проверь тормоза, задние фары немного тускловаты». Ты сам решаешь, что критично, а что подождёт.

Сохранение отчёта:

```bash
sudo lynis audit system --report-file /tmp/lynis-report.dat
```

---

## 7.2 Реальный вывод lynis

В конце аудита lynis выводит итоговый блок:

# Пример вывода (финальный раздел):
```
================================================================================
  Lynis security scan details:

  Hardening index : 67 [#############       ]
  Tests performed : 218
  Plugins enabled : 0

  Components:
  - Firewall               [V]
  - Malware scanner        [X]

  Lynis modules:
  - Compliance status      [?]
  - Security audit         [V]
  - Vulnerability scan     [V]

  Files:
  - Test and debug information      : /var/log/lynis.log
  - Report data                     : /var/log/lynis-report.dat

================================================================================

 -[ Lynis 3.0.8 Results ]-

  Warnings (3):
  ----------------------------
  ! Found one or more vulnerable packages [PKGS-7392]
      https://cisofy.com/lynis/controls/PKGS-7392/

  ! SSH PermitRootLogin is set to yes [SSH-7412]
      https://cisofy.com/lynis/controls/SSH-7412/

  ! No password set for single user mode [AUTH-9308]
      https://cisofy.com/lynis/controls/AUTH-9308/

  Suggestions (14):
  ----------------------------
  * Consider hardening SSH configuration [SSH-7408]
    - Details  : AllowTcpForwarding (set YES to NO)
    - https://cisofy.com/lynis/controls/SSH-7408/

  * Install a file integrity tool to monitor changes [FINT-4350]
    - https://cisofy.com/lynis/controls/FINT-4350/

  * Install libpam-tmpdir to set $TMP and $TMPDIR for PAM sessions [CUST-0280]
    - https://cisofy.com/lynis/controls/CUST-0280/

================================================================================
```

Ключевые числа: `Hardening index` (0–100) и список Warnings/Suggestions.

---

## 7.3 Как читать вывод и что значит score

| Hardening index | Что это значит | Что делать |
|---|---|---|
| 80–100 | Отличная база, enterprise-уровень | Поддерживать и проверять регулярно |
| 65–79 | Хорошая база для личного сервера | Закрыть Warnings, часть Suggestions |
| 50–64 | Средний уровень, есть пробелы | Исправить все Warnings приоритетно |
| < 50 | Слабая защита | Пройти заново по главам 1–6 |

**Score 65–70 для домашнего сервера — это нормально.** Часть рекомендаций lynis рассчитана на enterprise (bootloader password, SELinux, аудит ядра) и для личного VPS бессмысленна. Score 40 — плохо: значит не сделаны базовые вещи из этой книги.

---

## 7.4 Топ предупреждений: что исправить, а что можно пропустить

**Реально стоит исправить:**

| Warning / Suggestion | Почему важно |
|---|---|
| SSH PermitRootLogin is set to yes [SSH-7412] | Прямой вход root — большой риск, глава 1 |
| Found vulnerable packages [PKGS-7392] | Старые пакеты = известные уязвимости, глава 5 |
| No firewall active [FIRE-4512] | Сервер открыт без фильтрации, глава 3 |

**Можно игнорировать для домашнего сервера:**

| Suggestion | Почему не критично |
|---|---|
| Set password for bootloader [BOOT-5122] | На VPS нет физического доступа к GRUB |
| Install file integrity tool [FINT-4350] | AIDE/Tripwire — сложно, не нужно для начала |
| Enable SELinux/AppArmor [MACF-6234] | Это отдельная тема, не базовый hardening |

---

## 7.5 Пример предупреждения

```
! SSH PermitRootLogin is set to yes [SSH-7412]
    https://cisofy.com/lynis/controls/SSH-7412/
```

- `!` — это Warning (серьёзнее, чем Suggestion `*`)
- `SSH-7412` — ID контрола, по нему ищешь документацию
- URL ведёт на описание проблемы и способ исправления

Исправление: в `/etc/ssh/sshd_config` установи `PermitRootLogin no`, перезапусти sshd.

---

## 7.6 До и после

Запусти lynis до hardening и после. Сравни не только score, но и список важных предупреждений.

---

## 7.7 Практика

Сохрани два отчёта:

```text
lynis-before.dat
lynis-after.dat
```

Проверка: ты можешь объяснить три главных warning своими словами.
