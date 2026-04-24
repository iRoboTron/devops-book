# Ansible: Управление конфигурацией

> Книга 9 курса DevOps

---

## Оглавление

### Подготовка

- [**Глава 0: Зачем Ansible и как он работает**](chapter-00.md)
  - Shell vs Ansible, agentless модель, установка

### Часть 1: Основы

- [**Глава 1: Inventory и ansible.cfg**](chapter-01.md)
  - Список серверов, группы, динамический inventory из Terraform

- [**Глава 2: Ad-hoc команды и модули**](chapter-02.md)
  - Быстрые команды, apt, service, copy, file

- [**Глава 3: Переменные**](chapter-03.md)
  - group_vars, host_vars, facts, register, when

- [**Глава 4: Первый playbook**](chapter-04.md)
  - Структура, tasks, handlers, идемпотентность

### Часть 2: Шаблоны и роли

- [**Глава 5: Templates (Jinja2)**](chapter-05.md)
  - Динамические конфиги, facts, условия, циклы

- [**Глава 6: Roles**](chapter-06.md)
  - Структура роли, ansible-galaxy, зависимости

### Часть 3: Продвинутые практики

- [**Глава 7: Vault — шифрование секретов**](chapter-07.md)
  - ansible-vault, CI интеграция

- [**Глава 8: Loops и conditions**](chapter-08.md)
  - Циклы, when, block/rescue

- [**Глава 9: Тестирование и отладка**](chapter-09.md)
  - --check, --diff, Molecule

### Приложения

- [**Приложение A: Шпаргалка команд**](appendix-a.md)
- [**Приложение B: Готовые конфиги**](appendix-b.md)
- [**Приложение C: Диагностика**](appendix-c.md)

---

## Главная идея

Ansible решает: **"одинаковая конфигурация на всех серверах"**.

```
Shell-скрипт:           Ansible:
./setup.sh              ansible-playbook setup.yml
↓                       ↓
последовательно         параллельно
не идемпотентно         идемпотентно
```

Идемпотентность: запусти дважды — результат одинаковый.

---

## Предварительные требования

- Модули 1–7 (DevOps 1.0)
- Модуль 8 (Terraform) — серверы из `terraform output`
- SSH-ключи к серверам

---

*Ansible: Управление конфигурацией — Курс DevOps, Модуль 9*
