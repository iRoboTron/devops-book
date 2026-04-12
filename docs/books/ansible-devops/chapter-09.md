# Глава 9: Тестирование и отладка

> **Запомни:** `--check` покажет что изменится. `--diff` покажет diff файлов. Используй ДО apply.

---

## 9.1 `--check` — dry-run

```bash
ansible-playbook site.yml --check
```

Покажет что изменится БЕЗ применения.

```bash
ansible-playbook site.yml --check --diff
```

Покажет diff для файлов и шаблонов.

---

## 9.2 Verbose

```bash
ansible-playbook site.yml -v    # коротко
ansible-playbook site.yml -vv   # подробнее
ansible-playbook site.yml -vvv  # очень подробно (для отладки)
```

---

## 9.3 `debug` — вывод переменных

```yaml
- debug:
    var: nginx_status

- debug:
    msg: "Сервер: {{ inventory_hostname }}, IP: {{ ansible_default_ipv4.address }}"
```

---

## 9.4 `assert` — проверка условий

```yaml
- assert:
    that:
      - ansible_memory_mb.real.total > 512
    fail_msg: "Недостаточно RAM: нужно минимум 512MB"
    success_msg: "RAM OK: {{ ansible_memory_mb.real.total }}MB"
```

---

## 9.5 Molecule — тестирование ролей

```bash
pip install molecule molecule-plugins[docker]
molecule init role myapp
molecule test
```

Запускает роль в Docker-контейнере и проверяет результат.

> **Когда нужен:** роль используется несколькими людьми/проектами.

---

## 📝 Упражнения

### Упражнение 9.1: --check
**Задача:**
1. `ansible-playbook site.yml --check --diff`
2. Что изменилось бы?
3. Примени: `ansible-playbook site.yml`

### Упражнение 9.2: assert
**Задача:**
1. Добавь assert для проверки RAM > 256MB
2. Запусти — прошло?

---

## 📋 Чеклист главы 9

- [ ] Я использую `--check` перед apply
- [ ] Я могу использовать `--diff` для просмотра изменений
- [ ] Я могу использовать `-vvv` для отладки
- [ ] Я понимаю `assert` для проверок

**Всё отметил?** Книга 9 завершена!
