# Meta-prompt: сгенерировать мастер-ТЗ и ТЗ по книгам для части 3

Скопируй этот промт и отдай другому ИИ, если хочешь, чтобы он сгенерировал или переработал мастер-ТЗ и ТЗ по каждой книге части 3.

---

Ты работаешь в репозитории курса DevOps по пути `/home/adelfos/Documents/lessons/dev-ops`.

Твоя задача: подготовить комплект `AGENT-INSTRUCTIONS` для новой части курса:

- мастер-ТЗ для всей части;
- отдельные ТЗ для 7 книг;
- всё должно совпадать по стилю с уже существующими файлами `docs/books/AGENT-INSTRUCTIONS*.md`.

## Что нужно изучить перед генерацией

Прочитай:

- `docs/books/AGENT-INSTRUCTIONS.md`
- `docs/books/AGENT-INSTRUCTIONS-module-03.md`
- `docs/books/AGENT-INSTRUCTIONS-module-06.md`
- `docs/books/AGENT-INSTRUCTIONS-module-14.md`
- `docs/books/PART-03-security-architecture.md`

## Что нужно создать или обновить

1. `docs/books/AGENT-INSTRUCTIONS-part-03-security.md`
2. `docs/books/AGENT-INSTRUCTIONS-module-15.md`
3. `docs/books/AGENT-INSTRUCTIONS-module-16.md`
4. `docs/books/AGENT-INSTRUCTIONS-module-17.md`
5. `docs/books/AGENT-INSTRUCTIONS-module-18.md`
6. `docs/books/AGENT-INSTRUCTIONS-module-19.md`
7. `docs/books/AGENT-INSTRUCTIONS-module-20.md`
8. `docs/books/AGENT-INSTRUCTIONS-module-21.md`

## Контекст новой части

Это отдельная часть курса, полностью посвящённая защите и безопасной проверке своей защиты.

Аудитория:
- программист;
- поверхностно знаком с сетью;
- не эксперт по серверам и security;
- хочет дойти от home lab до архитектуры для VPS, small business и enterprise.

## Жёсткие ограничения

Нельзя:
- писать offensive playbook для злоупотребления;
- генерировать вредоносный код;
- давать инструкции для атак на чужие системы;
- делать курс зависимым от Windows/AD hands-on.

Можно:
- теория атак;
- lab-only демонстрации на своих VM/контейнерах;
- безопасные проверки своей защиты;
- intentionally vulnerable demo apps в изолированной среде;
- defensive use of tools like `nmap`, `tcpdump`, `wireshark`, `suricata`, `trivy`, `fail2ban`, `wazuh`.

## Архитектура части

Новая часть состоит из 7 книг:

1. Защита от внешних атак
2. Web Security для программиста
3. Сетевая защита и защитные устройства
4. Cloud, Docker и Kubernetes Security
5. Detection, Monitoring, Incident Response
6. Attacker Mindset для защитника
7. Security Architecture: от дома до организации

## Требования к мастер-ТЗ

Мастер-ТЗ должно:
- объяснить цели всей части;
- задать тон, стиль и безопасность содержания;
- описать структуру каждой книги;
- задать общие правила для lab-only практики;
- перечислить допустимые инструменты;
- показать progression от home lab до enterprise;
- зафиксировать, что книги должны быть самостоятельными и подробными, даже если местами повторяются.

## Требования к ТЗ каждой книги

Каждое ТЗ по книге должно включать:
- название;
- место в части;
- контекст;
- целевую аудиторию;
- кому особенно полезно: дом / VPS / small business / enterprise / всем;
- главную идею;
- структуру глав;
- итоговый проект;
- ограничения offensive-части;
- что важно не делать.

## Особое требование к первой книге

Для первой книги итоговый проект должен иметь 3 варианта:

1. один защищённый публичный Linux-сервер;
2. gateway + DMZ + app server;
3. lab со сценариями атак и доказательством работы защиты.

## Выходной формат

Сначала покажи:
- краткую архитектуру всей части;
- список файлов, которые создашь/обновишь;
- короткое обоснование, почему web security выделена в отдельную книгу.

Потом выдай содержимое файлов в готовом Markdown-формате.

Пиши по-русски. Стиль — инженерный, практический, без воды.
