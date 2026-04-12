# Глава 8: Loops и conditions

> **Запомни:** Не пиши 10 одинаковых задач. Один loop — 10 итераций.

---

## 8.1 `loop` — список

```yaml
- name: Установить пакеты
  apt:
    name: "{{ item }}"
    state: present
  loop:
    - nginx
    - python3
    - git
    - htop
```

---

## 8.2 `loop` со словарями

```yaml
- name: Создать пользователей
  user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
  loop:
    - { name: alice, groups: sudo }
    - { name: bob, groups: www-data }
```

---

## 8.3 `when` — условие

```yaml
- name: Установить nginx
  apt:
    name: nginx
  when: ansible_os_family == "Debian"

- name: Перезапустить если изменился
  service:
    name: nginx
    state: reloaded
  when: nginx_config.changed
```

---

## 8.4 `block / rescue / always`

```yaml
- block:
    - name: risky task
      command: /usr/local/bin/risky-script

  rescue:
    - name: откатить
      command: /usr/local/bin/rollback

  always:
    - name: лог
      debug:
        msg: "Task completed (or failed)"
```

Как try/catch/finally.

---

## 📝 Упражнения

### Упражнение 8.1: Loop
**Задача:**
1. Создай loop для установки 5 пакетов
2. Запусти — все 5 установились?

### Упражнение 8.2: when
**Задача:**
1. Создай задачу только для Ubuntu
2. Запусти на разных серверах — сработала только на Ubuntu?

---

## 📋 Чеклист главы 8

- [ ] Я могу использовать `loop` для списков и словарей
- [ ] Я могу использовать `when` для условий
- [ ] Я понимаю `block / rescue / always`

**Всё отметил?** Переходи к Главе 9 — Тестирование.
