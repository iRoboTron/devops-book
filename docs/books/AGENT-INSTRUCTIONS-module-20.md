# Инструкция для ИИ-агента: Модуль 20 — Attacker Mindset для защитника

> **Это шестая книга части 3.**
> Она должна быть самой осторожной по подаче: много теории, безопасные lab-only демонстрации, ноль боевых offensive-рецептов.

---

## Контекст проекта

Читатель уже строит защиту, но не понимает мышление атакующего. Из-за этого защита превращается в набор случайных настроек.

Нужно дать:
- kill chain;
- типовые пути атаки;
- признаки на каждом этапе;
- defensive takeaway после каждого этапа;
- безопасные демонстрации на собственном стенде.

---

## Что за книга

**Название:** "Attacker Mindset для защитника: Kill chain, TTP и безопасные демонстрации"

**Каталог:** `attacker-mindset-devops`

**Для кого особенно полезна:**
- всем;
- особенно тем, кто строит защиту "по чеклисту" и хочет понять противника.

**Объём:** 150-190 страниц

---

## Главная идея книги

Читатель не должен выйти "маленьким хакером". Он должен выйти защитником, который понимает:

- как атакующий выбирает цель;
- какие сигналы оставляет;
- какие слабости ищет;
- где можно прервать цепочку атаки.

---

## Структура книги

### Глава 0: Этические и лабораторные границы
- только свои стенды;
- snapshots;
- isolated networks;
- no production;
- no third-party targets.

### Глава 1: Reconnaissance
- passive vs active;
- DNS, headers, banners;
- what defenders expose unintentionally.

### Глава 2: Initial access
- weak passwords;
- exposed services;
- outdated software;
- phishing theory only;
- misconfigurations.

### Глава 3: Credential abuse
- reused passwords;
- leaked secrets;
- missing MFA;
- defensive logging and prevention.

### Глава 4: Privilege escalation theory
- sudo, SUID, bad permissions;
- container misconfig;
- theory + safe local demos.

### Глава 5: Persistence theory
- startup services;
- cron;
- user accounts;
- SSH keys;
- what defenders should baseline and watch.

### Глава 6: Lateral movement theory
- pivoting concepts;
- shared credentials;
- flat networks;
- why segmentation matters.

### Глава 7: Exfiltration and impact theory
- staging;
- DNS/HTTP exfil concepts;
- encryption and backups;
- blast radius control.

### Глава 8: Safe demonstrations
- banner grabbing on own lab;
- noisy scan;
- failed login storm on own VM;
- weak sudo demo on local container/VM;
- detection and mitigation after each demo.

### Глава 9: Итоговый проект
- построить defensive narrative по kill chain на своём стенде;
- показать, где цепочка ломается благодаря защите.

---

## Особое требование

После каждой offensive-темы должен быть блок:

- что увидит защитник;
- как ограничить риск;
- как обнаружить;
- как восстановиться.
