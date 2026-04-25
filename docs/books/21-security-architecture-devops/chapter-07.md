# Глава 7: Интеграция Linux в большую организацию

> **Запомни:** Linux-хост в большой организации живет не сам по себе: он должен встроиться в общие процессы идентификации, логирования, обновлений и инцидентного реагирования.

---

## 7.1 Контекст и границы

Даже если сам хост идеально настроен, в большой организации важны интеграции: централизованный доступ, inventory, patching, logging, backup, vulnerability management, ownership и change process.

Эта тема нужна, чтобы понимать, как Linux перестает быть отдельной коробкой и становится управляемым активом компании.

Эта глава особенно полезна для тех, кто думает о Linux в enterprise-контексте без ухода в Windows и AD hands-on.

---

## 7.2 Как выглядит риск

Типовые слабые места:
- локальные учетки живут отдельно от общего IAM — увольнение или смена роли не приводят к автоматическому отзыву доступа.
  Проверить: inventory users и связь с owner.
- хост не виден в inventory и сканировании — актив существует, но не живёт в общем процессе.
  Проверить: наличие asset record и owner.
- патчи ставятся вручную и непредсказуемо — один хост выпадает из цикла обновлений и становится слабым местом.
  Проверить: patch cadence и список последних обновлений.
- логи не уходят в центральный контур — расследование останавливается на локальном journald.
  Проверить: log shipping и retention.
- нет owner и процесса изменений — Linux-хост превращается в бесхозный актив.
  Проверить: lifecycle, change owner и backup owner.

### Где особенно важно
- enterprise Linux fleet
- platform teams
- regulated environments
- hybrid infra

---

## 7.3 Что строит защитник

- интеграция с централизованной аутентификацией или как минимум управляемыми локальными учетками;
- inventory и owner;
- patch cadence и контроль уязвимостей;
- централизованный сбор логов;
- процесс изменения, бэкапа и вывода из эксплуатации.

### Практический результат главы
- ты понимаешь, чего от Linux-хоста ждут в большой организации;
- можешь описать минимальный enterprise-ready baseline без привязки к одному вендору;
- умеешь видеть организационные, а не только технические разрывы.

```
- owner
- inventory entry
- patch schedule
- central logs
- backup policy
- admin access policy
```

---

## 7.4 Практика

### Шаг 1: Собери enterprise baseline для узла
- опиши, какие интеграции нужны хосту: IAM, logs, patches, backups, inventory;
- для каждой укажи, что уже есть, а что нет.

```bash
cat > /tmp/enterprise-host-baseline.txt <<'EOF'
owner
inventory
logs
patching
backup
EOF
cat /tmp/enterprise-host-baseline.txt
```

### Шаг 2: Проверь owner и lifecycle
- у каждого хоста должен быть владелец, назначение и процедура вывода из эксплуатации;
- без этого актив становится бесхозным риском.

```bash
cat > /tmp/asset-lifecycle.txt <<'EOF'
owner: platform
purpose: internal app host
patch window: monthly
backup policy: daily
retirement: decommission checklist required
EOF
cat /tmp/asset-lifecycle.txt
```

### Шаг 3: Сравни с текущей lab
- какие enterprise-практики уже можно применять у себя: owners, central logs, patch schedule, inventory;
- не жди большого масштаба, чтобы начать.

```bash
cat > /tmp/small-scale-enterprise-habits.txt <<'EOF'
inventory
owner
patch schedule
central logs
backup policy
EOF
cat /tmp/small-scale-enterprise-habits.txt
```

## 7.5 Как архитектура масштабируется

| Уровень | Периметр | Auth | Секреты | Мониторинг |
|---------|----------|------|---------|------------|
| Дом | `ufw` | SSH-ключи | `.env` + `chmod 600` | `journalctl` |
| VPS | `ufw` + cloud SG | SSH + fail2ban | `.env` + права | Grafana / basic alerts |
| Small biz | pfSense/OPNsense | VPN + MFA | Vault/SOPS | Central logs / SIEM basic |
| Enterprise | NGFW + WAF | SSO + MFA + PAM | Vault/KMS | SIEM + SOC |

Принцип не меняется: defence in depth остаётся тем же, просто на каждом уровне меняются инструменты и количество владельцев.

### Что нужно явно показать
- какие организационные интеграции нужны Linux-хосту;
- как выглядит owner, lifecycle, patching и logging baseline;
- что из этого уже переносимо в маленький проект;
- какие gaps остаются.

---

## 7.6 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- возьми одну свою VM и опиши ее как enterprise asset: owner, назначение, patch schedule, backup policy, log shipping, admin access;
- сравни это с ее текущим состоянием и закрой 2-3 явных gap;
- это хорошее упражнение на зрелость даже без реального enterprise.

---

## 7.7 Типовые ошибки

- рассматривать Linux-хост как изолированную коробку;
- не назначать owner и lifecycle;
- не подключать хост к общему logging и patching процессу;
- считать enterprise-требования чисто бюрократией.

---

## 7.8 Чеклист главы

- [ ] Я понимаю, как Linux-хост встраивается в организационный контур
- [ ] У актива есть owner, lifecycle и patching baseline
- [ ] Логи, backup и admin access встроены в общий процесс
- [ ] Часть enterprise-привычек уже применима даже в моей lab
