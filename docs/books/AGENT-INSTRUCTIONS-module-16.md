# Инструкция для ИИ-агента: Модуль 16 — Web Security для программиста

> **Это вторая книга части 3.**
> Это отдельная большая тема и её нельзя сжимать до пары глав в другой книге.

---

## Контекст проекта

Читатель — программист. Он умеет писать backend/frontend, но не привык смотреть на приложение глазами защитника.

Ему нужно показать:
- где проходят trust boundaries;
- как типовые web-риски появляются в обычном коде;
- как конфигурация, reverse proxy и секреты влияют на безопасность;
- как безопасно проверять своё web-приложение в lab.

---

## Что за книга

**Название:** "Web Security для программиста: Приложение, конфигурация и безопасные проверки"

**Каталог:** `16-web-security-devops`

**Для кого особенно полезна:**
- всем;
- особенно backend/frontend разработчикам;
- владельцам API и административных панелей.

**Объём:** 170-220 страниц

---

## Главная идея книги

Безопасность web-приложения ломается не только "у хакеров", а в самых обычных местах:

- login/password reset;
- file upload;
- SQL запросы;
- шаблоны HTML;
- cookies/session storage;
- proxy headers;
- секреты и `.env`;
- доверие к внутренним сервисам.

Книга должна дать и объяснение, и защитную практику, и безопасную лабораторную проверку.

---

## Структура книги

### Глава 0: Threat model веб-приложения
- assets;
- users, admins, attackers;
- trusted/untrusted input;
- интернет, браузер, reverse proxy, app, DB.

### Глава 1: Аутентификация, сессии и reset flow
- password hashing;
- session cookies;
- secure, httponly, samesite;
- reset token lifecycle;
- типовые ошибки.

### Глава 2: SQLi и безопасная работа с БД
- параметры вместо конкатенации;
- ORM не гарантирует безопасность;
- безопасная демонстрация на локальном стенде;
- что видно в логах.

### Глава 3: XSS, output encoding и CSP basics
- stored/reflected XSS;
- template escaping;
- CSP как дополнительный слой;
- безопасные демонстрации на intentionally vulnerable demo app.

### Глава 4: CSRF, CORS и browser trust boundaries
- CSRF tokens;
- CORS myths;
- same-origin policy;
- SPA/API нюансы.

### Глава 5: SSRF, file upload и работа с внешними ресурсами
- SSRF class of bugs;
- metadata endpoints;
- file validation;
- storage isolation;
- безопасная lab-only проверка.

### Глава 6: Secrets, `.env`, headers и reverse proxy security
- секреты не в git;
- forward headers;
- host header;
- security headers;
- admin panels behind VPN or allowlist.

### Глава 7: Dependency, supply chain и unsafe defaults
- зависимости;
- SCA basics;
- npm/pip lockfiles;
- минимально достаточные права.

### Глава 8: Безопасные инструменты проверки
- `curl`, browser devtools;
- `nikto` и аналогичные инструменты только против своего стенда;
- SAST/DAST basics;
- что реально полезно программисту.

### Глава 9: Итоговый проект
- привести учебное web-приложение к defensible baseline;
- доказать защиту контролируемыми проверками.

---

## Итоговый проект

Основной проект:
- есть intentionally weak demo app или собственное приложение;
- читатель по шагам убирает типовые web-риски;
- включает безопасные cookie flags, headers, rate limiting, secret handling;
- проводит безопасные lab-only проверки;
- фиксирует результаты в чеклисте.

Альтернативный вариант:
- API-only сервис за reverse proxy;
- безопасность токенов, CORS, SSRF и admin endpoints.

---

## Границы offensive-материала

Разрешено:
- теория;
- безопасные демонстрации на локально уязвимом стенде;
- атака только против собственных demo apps.

Запрещено:
- публикация exploit chain для чужих систем;
- вредоносные payload generator'ы;
- инструкции по реальной эксплуатации третьих лиц.
