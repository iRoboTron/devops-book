# Инструкция агенту: улучшение книги 21 «Security Architecture: от дома до организации»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/21-security-architecture-devops/
```

Книга: 1199 строк. Завершающая книга всего курса — архитектурный взгляд на безопасность. Главные проблемы:
1. **Заглушки `printf`** вместо реальных команд в практических разделах
2. Глава 6 (Security roadmap) — приоритизация описана абстрактно (P1/P2/P3), но нет критериев почему конкретная задача попадает в P1
3. Финальный проект — нет measurable criteria, как доказать что архитектура правильная

---

## Замена заглушек `printf`

Найти все конструкции вида `printf '...\n'` в практических разделах и заменить реальными командами. Типичные контексты:
- «собери backlog» → конкретная команда audit
- «сделай inventory» → `ss -tulpn`, `systemctl list-units`, `nmap`
- «проверь восстановление» → конкретный test-restore

---

## Задачи по главам

---

### Глава 1 (`chapter-01.md`) — Домашняя лаборатория

**Добавить** в раздел 1.4 конкретные проверочные команды для home lab:

```bash
# Инвентаризация устройств в своей сети
ip neigh show
# или с nmap (только своя сеть!)
nmap -sn 192.168.1.0/24

# Проверить что VM имеет снапшот
virsh list --all
virsh snapshot-list VM_NAME

# Или в VirtualBox
VBoxManage list vms
VBoxManage snapshot VM_NAME list
```

**Добавить** раздел **1.5 «Проверить восстановление» (самое важное)**:

```bash
# Тест: откатить VM к снапшоту и убедиться что она работает
virsh snapshot-revert VM_NAME SNAPSHOT_NAME
virsh start VM_NAME
# Подождать и проверить:
ssh user@VM_IP echo "restored OK"
```

Если не откатывалось никогда — откат не работает. Проверять раз в месяц.

---

### Глава 2 (`chapter-02.md`) — VPS паттерн

**Добавить** итоговую проверку «всё что нужно на VPS»:

```bash
# Проверочный скрипт для VPS baseline
echo "=== SSH hardening ==="
sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries'

echo "=== Firewall ==="
sudo ufw status verbose | head -15

echo "=== Открытые порты ==="
ss -tulpn | grep LISTEN

echo "=== Последние логины ==="
last -n 10 -a

echo "=== Обновления ==="
apt list --upgradable 2>/dev/null | grep -c upgradable
echo " пакетов требуют обновления"
```

Все проверки в одном скрипте — запускать после каждого деплоя.

---

### Глава 3 (`chapter-03.md`) — Small business паттерн

**Добавить** раздел **3.5 «Inventory инфраструктуры»** с реальными командами:

```bash
# Собрать список всех сервисов
systemctl list-units --type=service --state=running --no-pager | \
  awk '{print $1, $4}' | grep -v UNIT

# Список слушающих портов с процессами
ss -tulpn | grep LISTEN | awk '{print $5, $7}'

# Список открытых портов снаружи (со второй машины)
nmap -Pn SERVER_IP -oG - | grep "open"
```

Сохранить вывод как `inventory-$(date +%Y%m%d).txt` — это baseline для сравнения при следующем audit.

---

### Глава 6 (`chapter-06.md`) — Security roadmap

**Главная проблема:** P1/P2/P3 описаны но нет критериев почему задача попадает в P1, а не P2.

**Заменить раздел 6.2** (заглушку с printf) на реальный процесс приоритизации:

**Матрица приоритизации — как решить где P1:**

| Критерий | P1 (сейчас) | P2 (в ближайшие 2-3 мес) | P3 (потом) |
|----------|-------------|--------------------------|------------|
| Impact если реализуется | Потеря данных / недоступность > 4ч | Утечка данных / доступность 1-4ч | Неудобство / частичные данные |
| Вероятность | Активно эксплуатируется в мире | Реальный вектор | Теоретический |
| Стоимость исправления | Часы | Дни | Недели |

**Конкретные примеры P1** (то что нужно сделать до всего остального):

```
✅ backup не существует или никогда не проверялся на восстановление
✅ SSH принимает парольную аутентификацию с интернета
✅ root login разрешён по SSH
✅ нет firewall или открыты БД наружу
✅ .env с реальными секретами в git репозитории
✅ все пользователи работают под root / нет разделения прав
```

**P2** (важно, но не блокирует):
```
секреты в переменных окружения без ротации
нет rate limiting на auth endpoints
нет централизованных логов
устаревшие пакеты с CVE
```

**P3** (когда P1 и P2 закрыты):
```
IDS/IPS
SIEM интеграция
WAF перед приложением
advanced threat hunting
```

**Добавить** раздел **6.5 «Как провести security audit за 1 час»:**

```bash
#!/bin/bash
# security-quick-audit.sh — запускать раз в квартал

echo "=== [1] SSH ==="
sshd -T | grep -E 'permitrootlogin|passwordauthentication'

echo "=== [2] Firewall ==="
sudo ufw status | head -5

echo "=== [3] Открытые порты ==="
ss -tulpn | grep LISTEN

echo "=== [4] Права на .env файлы ==="
find /opt /home -name ".env" 2>/dev/null -exec ls -la {} \;

echo "=== [5] Последние изменения sudoers ==="
stat /etc/sudoers | grep Modify

echo "=== [6] Новые пользователи (последние 30 дней) ==="
awk -F: '{print $1, $3}' /etc/passwd | sort -t' ' -k2 -n | tail -5

echo "=== [7] Обновления безопасности ==="
apt list --upgradable 2>/dev/null | grep -i security

echo "=== [8] Backup существует и свежий ==="
find /var/backups -name "*.sql" -o -name "*.tar.gz" 2>/dev/null | \
  xargs -I{} stat {} | grep Modify | sort -r | head -3
```

Вывод показывает текущее состояние — по результатам строить roadmap.

---

### Глава 7 (`chapter-07.md`) — Enterprise и cloud паттерны

**Добавить** раздел **7.5 «Как архитектура масштабируется»:**

Показать что один и тот же принцип (defence in depth) работает на всех уровнях, просто инструменты разные:

| Уровень | Периметр | Auth | Секреты | Мониторинг |
|---------|----------|------|---------|------------|
| Дом | ufw | SSH ключи | .env (chmod 600) | journalctl |
| VPS | ufw + cloud SG | SSH + fail2ban | .env + chmod | Grafana |
| Small biz | pfSense/OPNsense | VPN + MFA | Vault/SOPS | SIEM basic |
| Enterprise | NGFW + WAF | SSO + MFA + PAM | Vault/KMS | SIEM + SOC |

Принцип не меняется — меняется масштаб инструментов.

---

### Глава 9 (`chapter-09.md`) — Итоговый проект

**Добавить** в раздел 9.3 измеримые критерии для каждой фазы:

**Фаза 1 (Карта активов) — пройдена если:**

```bash
# Можешь ответить на вопросы:
echo "Публичные endpoints:" && curl -s https://SERVER_IP/ -o /dev/null -w "%{http_code}\n"
echo "Открытые порты снаружи:" && nmap -Pn SERVER_IP 2>/dev/null | grep "open"
echo "Слушающие сервисы:" && ss -tulpn | grep LISTEN | wc -l
```

**Фаза 2 (Controls) — пройдена если:**

```bash
# Все P1 проверки зелёные:
sshd -T | grep "passwordauthentication no"    # SSH без пароля
sshd -T | grep "permitrootlogin no"           # root запрещён
sudo ufw status | grep "Status: active"       # firewall включён
ls /var/backups/*.sql 2>/dev/null | wc -l     # бэкап существует
```

**Финальный критерий всего проекта:**

```bash
# Сможешь ли ты восстановить с нуля?
# 1. Сделай terraform destroy (если облако)
# 2. Выполни: terraform apply && ansible-playbook && ArgoCD sync
# 3. Проверь:
curl https://yourdomain.com/health   # 200 OK
psql -c "SELECT COUNT(*) FROM users"  # данные на месте

# Время восстановления < 30 минут?
# Если да — архитектура правильная
```

---

## Приоритет

1. Глава 6 (Roadmap) — заменить абстрактный P1/P2/P3 на матрицу с конкретными критериями + скрипт quick audit
2. Заменить все `printf`-заглушки реальными командами
3. Глава 9 (Проект) — измеримые критерии фаз
4. Глава 1 (Home lab) — добавить тест-restore snapshot

---

## Общая инструкция для всех книг 17–21

Помимо специфических правок — применить ко **всем** разделам «Типовые слабые места» (X.2) следующий формат:

```
Текущий формат (плохо):
- открытая рекурсия

Правильный формат:
- **Открытая рекурсия** — сервер отвечает на DNS-запросы от любого IP в интернете.
  Используется в DNS Amplification DDoS: маленький запрос (40 байт) → большой ответ (4KB) к жертве.
  Проверить: `dig @YOUR_SERVER any google.com` с внешней машины. Ответ пришёл = проблема.
```

Механика (1 предложение) + impact (1 предложение) + команда проверки. Без этих трёх элементов — оставить в списке без изменений.

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-21-improve.md`*
