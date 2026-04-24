# Terraform: Инфраструктура как код

> Книга 8 курса DevOps — первая в DevOps 2.0

---

## Оглавление

### Подготовка

- [**Глава 0: Зачем Terraform и что такое IaC**](chapter-00.md)
  - Проблема ручных серверов, IaC vs shell-скрипты, установка

### Часть 1: Основы

- [**Глава 1: Первый ресурс — читаем terraform plan**](chapter-01.md)
  - null/local провайдеры, plan/apply цикл, идемпотентность

- [**Глава 2: Переменные, outputs и data sources**](chapter-02.md)
  - variable, output, типы, .tfvars, .gitignore

- [**Глава 3: Locals, выражения и функции**](chapter-03.md)
  - locals, join, lookup, try, count

- [**Глава 4: Первый сервер — полный ресурс**](chapter-04.md)
  - Hetzner VPS + Firewall + SSH-ключ + Ansible inventory

### Часть 2: State и организация

- [**Глава 5: State-файл — сердце Terraform**](chapter-05.md)
  - tfstate, remote backend, import, lock

- [**Глава 6: Modules — переиспользуемые блоки**](chapter-06.md)
  - Структура модуля, вызов, публичные модули

### Часть 3: Рабочий процесс

- [**Глава 7: Workspaces — dev/staging/prod**](chapter-07.md)
  - Workspaces, locals для окружений

- [**Глава 8: Terraform + CI/CD**](chapter-08.md)
  - GitHub Actions: plan на PR, apply на merge

- [**Глава 9: Опасные операции**](chapter-09.md)
  - destroy, taint, import, lifecycle, prevent_destroy

### Приложения

- [**Приложение A: Шпаргалка команд**](appendix-a.md)
- [**Приложение B: Готовые конфиги**](appendix-b.md)
- [**Приложение C: Диагностика**](appendix-c.md)

---

## Главная идея

Terraform решает одну проблему: **"я не помню как это было настроено"**.

```
Без Terraform:          С Terraform:
Сервер упал             terraform destroy
↓                       terraform apply
3 часа вспоминать       ↓
что настраивал          5 минут — всё готово
```

- IaC — не про скорость. Про воспроизводимость.
- `terraform plan` — самый важный шаг
- State-файл — сердце Terraform
- `terraform destroy` — такой же инструмент как `apply`

---

## Как пользоваться книгой

1. **Читай по порядку** — главы строятся друг на друге
2. **Главы 1–2 БЕЗ облака** — null/local провайдеры, локальная практика
3. **Глава 3+** — реальный сервер (Hetzner)
4. **Делай упражнения** — особенно проверку идемпотентности
5. **Отмечай чеклисты** — в конце каждой главы

## Предварительные требования

- Пройдены Модули 1–7 (DevOps 1.0)
- Умение работать в терминале
- SSH-ключи, GitHub-аккаунт
- Для глав 4+: аккаунт Hetzner Cloud (или другой провайдер)

---

*Terraform: Инфраструктура как код — Курс DevOps, Модуль 8*
