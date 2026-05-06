# Приложение B: Severity и false positives

## Severity

Critical: прямо сейчас есть высокий шанс серьёзного ущерба. Пример: админка без пароля открыта наружу.

High: серьёзная проблема, но есть смягчающие факторы. Пример: устаревший образ с high CVE, сервис доступен только через VPN.

Medium: нужно исправить, но можно планировать. Пример: неидеальные headers.

Low/Info: полезная информация. Пример: раскрывается версия сервера без реального риска.

## False positive

False positive не значит "инструмент плохой". Это значит, что находку надо проверить в контексте.

Шаблон:

```markdown
Finding:
Tool:
Evidence:
Why it is false positive / accepted risk:
Review date:
```

**Заполненные примеры:**

```markdown
Finding: X-XSS-Protection header is not defined
Tool: nikto v2.1.6
Evidence: nikto.txt строка 47
Why it is false positive: Заголовок X-XSS-Protection устарел и удалён из Chrome 78+,
Firefox 57+. Добавление его не улучшит безопасность. Современные браузеры используют
Content-Security-Policy вместо него.
Review date: не требует пересмотра
```

```markdown
Finding: /phpmyadmin/ directory found
Tool: nikto v2.1.6
Evidence: nikto.txt строка 51; проверка: curl -I https://myapp.example.com/phpmyadmin/ → HTTP/1.1 404
Why it is false positive: nikto проверяет путь по словарю. На сервере phpMyAdmin не установлен.
Nginx возвращает 404. Реальной директории нет.
Review date: следующий аудит 2026-08-06
```

```markdown
Finding: CVE-2005-2541 LOW tar — does not check for symlinks in world-writable directories
Tool: trivy image nginx:latest
Evidence: trivy-nginx.txt строка 203
Why it is false positive / accepted risk: tar внутри nginx контейнера не используется
во время работы сервиса. Контейнер не обрабатывает tar-архивы от пользователей.
Fixed version: (not fixed) — уязвимость признана особенностью поведения.
Принятый риск. Пересмотреть если изменится use case.
Review date: следующий аудит 2026-08-06
```

## План внедрения

### За 1 день

Scope, nmap, TLS, headers.

### За 1 неделю

Nikto, Trivy, Lynis, logs.

### За 1 месяц

Исправить high/critical, повторить проверки, поставить квартальный график.
