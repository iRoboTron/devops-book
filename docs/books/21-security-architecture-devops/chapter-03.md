# Глава 3: Small business pattern

> **Запомни:** малый бизнес требует уже не просто одного сервера, а повторяемого паттерна: gateway, зоны, управление доступом, наблюдаемость и понятный операционный ритм.

---

## 3.1 Контекст и границы

В small business архитектуре появляется важный переход: инфраструктура должна переживать не только техническую ошибку, но и смену людей, рост числа сервисов и несколько сценариев инцидентов.

Здесь начинают оправдываться gateway, VPN, management zone, central logs и минимальная формализация ролей.

Эта глава особенно полезна для малых офисов, маленьких команд и нескольких публичных сервисов.

---

## 3.2 Как выглядит риск

Типовые слабые места:
- публичные и внутренние сервисы смешаны — случайная публикация внутреннего сервиса становится вопросом времени.
  Проверить: внешний `nmap` и список listeners на хостах.
- одни и те же учетки используют все админы — ответственность и отзыв доступа не разделены.
  Проверить: admin users, sudo group и `authorized_keys`.
- нет центральных логов и общего inventory — команда не знает, где искать сервис и кто его владелец.
  Проверить: есть ли inventory и централизованный logging path.
- backup и recovery не распределены по приоритетам — всё восстанавливается "когда получится", а не по impact.
  Проверить: owners, RTO/RPO и backup criticality.
- сеть выросла, но осталась flat — lateral movement и операционный шум живут в одной зоне.
  Проверить: схема зон и межзонных потоков.

### Где особенно важно
- малый офис
- 2-5 серверов
- несколько SaaS + свой периметр

---

## 3.3 Что строит защитник

- gateway и firewall плюс VPN;
- management zone;
- разделение публичных сервисов и внутренних систем;
- минимальная CMDB или inventory;
- центральные логи, backup policy и owners.

### Практический результат главы
- ты понимаешь, как выглядит разумный security baseline для small business;
- можешь объяснить, зачем нужны gateway, зоны и inventory;
- умеешь проектировать без enterprise-переусложнения.

```
Интернет -> gateway/firewall -> DMZ/public apps
                 -> VPN -> management
                 -> internal services
```

---

## 3.4 Практика

### Шаг 1: Опиши бизнес-зоны
- выдели public, internal, management, backup и user сети;
- для каждой опиши owner и допустимые потоки.

```bash
cat > /tmp/small-business-zones.txt <<'EOF'
zone owner allowed_flows
public ops internet->443
management ops vpn->ssh
internal app app->db
backup ops restore-only
EOF
cat /tmp/small-business-zones.txt
```

### Шаг 2: Собери inventory
- список хостов, сервисов, доменов, credentials owners и backup критичности;
- без inventory архитектура неуправляема.

```bash
systemctl list-units --type=service --state=running --no-pager | \
  awk '{print $1, $4}' | grep -v UNIT
ss -tulpn | grep LISTEN | awk '{print $5, $7}'
nmap -Pn SERVER_IP -oG - 2>/dev/null | grep "open"
```

Сохрани этот вывод как baseline:

```bash
inventory_file="inventory-$(date +%Y%m%d).txt"
{
  systemctl list-units --type=service --state=running --no-pager
  ss -tulpn | grep LISTEN
} > "$inventory_file"
ls -l "$inventory_file"
```

### Шаг 3: Назначь минимальные operational процессы
- кто смотрит логи, кто отвечает за бэкапы, кто обновляет gateway, кто имеет admin access;
- это должно быть письменно, а не в памяти.

```bash
cat > /tmp/ops-ownership.md <<'EOF'
gateway owner: ops
backup owner: ops
public app owner: app team
logging owner: ops
admin access owner: security/ops
EOF
cat /tmp/ops-ownership.md
```

## 3.5 Inventory инфраструктуры

```bash
systemctl list-units --type=service --state=running --no-pager | \
  awk '{print $1, $4}' | grep -v UNIT
ss -tulpn | grep LISTEN | awk '{print $5, $7}'
nmap -Pn SERVER_IP -oG - 2>/dev/null | grep "open"
```

Это минимальный baseline для следующего аудита: какие сервисы живут внутри, какие порты слушают и что видно снаружи.

### Что нужно явно показать
- схему small business зон;
- inventory активов и owners;
- как устроены admin access и backup policy;
- какие процессы уже формализованы.

---

## 3.6 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- перерисуй свою lab как small business pattern: gateway, public, internal, management, backup;
- зафиксируй, какие элементы пока отсутствуют и как их можно добавить без enterprise-сложности;
- сравни стихийную и структурированную схему.

---

## 3.7 Типовые ошибки

- строить инфраструктуру без inventory;
- не разделять зоны по ролям;
- оставлять shared admin accounts;
- не формализовать хотя бы базовые операционные роли.

---

## 3.8 Чеклист главы

- [ ] Я понимаю архитектурный паттерн small business
- [ ] Есть inventory активов и owners
- [ ] Зоны public, internal, management и backup выделены
- [ ] Базовые процессы и роли описаны письменно
