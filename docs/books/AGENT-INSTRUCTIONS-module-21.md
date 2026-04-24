# Инструкция для ИИ-агента: Модуль 21 — Security Architecture: от дома до организации

> **Это седьмая и финальная книга части 3.**
> Она должна свести все предыдущие книги в архитектурные решения по масштабу.

---

## Контекст проекта

Читатель уже знает много отдельных механизмов защиты, но ему нужно увидеть:

- как всё соединяется в систему;
- что уместно дома, на одном VPS, в small business и в enterprise;
- какие решения выбирать по бюджету и риску;
- как не строить слишком слабую или слишком тяжёлую архитектуру.

---

## Что за книга

**Название:** "Security Architecture: От домашней лаборатории до крупной организации"

**Каталог:** `21-security-architecture-devops`

**Для кого особенно полезна:**
- VPS;
- small business;
- enterprise patterns;
- архитекторам и senior-практикам.

**Объём:** 170-220 страниц

---

## Главная идея книги

Технологии без архитектуры превращаются в набор разрозненных настроек.

Книга должна ответить:
- как собрать слои защиты в систему;
- как принимать решения по риску, бюджету и масштабу;
- как выглядит growth path:
  - дом;
  - VPS;
  - small business;
  - крупная организация.

---

## Структура книги

### Глава 0: Архитектурное мышление в security
- assets;
- trust zones;
- attack surface;
- control objectives.

### Глава 1: Домашняя лаборатория и personal infrastructure
- роутер;
- VPN;
- backup;
- segmentation;
- sane minimum.

### Глава 2: Один VPS / один публичный сервис
- bastion or VPN;
- CDN/WAF;
- host hardening;
- backup/recovery;
- simple detection stack.

### Глава 3: Small business
- gateway;
- VLAN;
- IAM basics;
- central logs;
- admin workstation hygiene;
- change management basics.

### Глава 4: Enterprise patterns
- zero trust concepts;
- central identity concepts;
- SSO/MFA;
- EDR/SIEM classes;
- secrets governance;
- software supply chain controls.

### Глава 5: Выбор решений и tradeoffs
- build vs buy;
- managed vs self-hosted;
- cloud vs on-prem signals;
- operational burden.

### Глава 6: Security roadmap
- что делать в первые 30/90/180 дней;
- quick wins;
- medium-term projects;
- long-term capabilities.

### Глава 7: Интеграция Linux-систем в большую организацию
- bastions;
- central auth concepts;
- logging;
- ticketing/runbooks;
- AD как внешний enterprise-контекст, без Windows hands-on.

### Глава 8: Reference architectures
- 4-5 ASCII схем;
- сравнение по стоимости, сложности, риску;
- где что оправдано.

### Глава 9: Итоговый проект
- выбрать один из масштабов;
- спроектировать целевую security-архитектуру;
- защитить решения аргументами и чеклистом.

---

## Итоговый проект

Формат:
- читатель выбирает один масштаб;
- описывает активы, угрозы, controls, monitoring, recovery;
- строит reference architecture;
- показывает, почему она достаточна и не перегружена.

---

## Особое требование

Не делай из книги governance-only материал. Она должна оставаться инженерной и практической, с реальными схемами, конфигами и операционными решениями.
