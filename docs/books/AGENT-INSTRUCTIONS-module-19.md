# Инструкция для ИИ-агента: Модуль 19 — Detection, Monitoring, Incident Response

> **Это пятая книга части 3.**
> Она должна ответить на вопрос: "что делать после того, как защита уже стоит, но события всё равно происходят?"

---

## Контекст проекта

Читатель уже знает базовую защиту, но ему не хватает:

- видимости;
- приоритизации сигналов;
- workflow реакции;
- уверенности, что он восстановится после инцидента.

---

## Что за книга

**Название:** "Detection, Monitoring и Incident Response: Сигналы, triage и восстановление"

**Каталог:** `19-incident-response-devops`

**Для кого особенно полезна:**
- всем;
- особенно владельцам публичных сервисов и командным проектам.

**Объём:** 170-220 страниц

---

## Структура книги

### Глава 0: Что считать инцидентом
- event vs alert vs incident;
- severity;
- assets;
- response time expectations.

### Глава 1: Логи как сырьё
- auth logs;
- web logs;
- app logs;
- audit trails;
- centralization basics.

### Глава 2: Метрики и алерты
- golden signals;
- security-relevant alerts;
- noisy vs actionable alerts.

### Глава 3: Host-level detection
- Wazuh/EDR-like visibility;
- file integrity monitoring;
- suspicious processes;
- scheduled tasks;
- baseline deviations.

### Глава 4: Triage
- что проверять первым;
- timeline;
- preserve evidence basics;
- isolation decisions.

### Глава 5: Recovery
- rollback;
- key rotation;
- host rebuild vs cleanup;
- backup verification.

### Глава 6: Ransomware resilience without ransomware practice
- immutable backups concepts;
- restore drills;
- blast radius reduction;
- detection indicators.

### Глава 7: Forensics basics
- what to collect;
- logs, configs, process tree, open sockets;
- hashes and chain of custody basics;
- practical limits for small teams.

### Глава 8: Tabletop and lab exercises
- controlled incident drills;
- alert to recovery scenarios;
- postmortem.

### Глава 9: Итоговый проект
- detect -> contain -> recover;
- runbook and checklist.

---

## Итоговый проект

Собрать стенд, где:
- генерируются контролируемые security-события;
- защита/мониторинг подают сигналы;
- читатель проводит triage;
- изолирует/исправляет;
- восстанавливает сервис;
- пишет короткий postmortem.

---

## Особое требование

Книга должна быть практичной, но не уходить в advanced digital forensics beyond reasonable limits. Это инженерная книга, а не курс криминалистики.
