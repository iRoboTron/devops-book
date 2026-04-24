# Приложение A: Шпаргалка команд

| Команда | Назначение |
|---------|-----------|
| `ansible all -m ping` | Проверить соединение |
| `ansible web -m setup` | Получить факты хоста |
| `ansible-playbook site.yml` | Запустить playbook |
| `ansible-playbook site.yml --check` | Dry-run |
| `ansible-playbook site.yml --diff` | Показать diff |
| `ansible-playbook site.yml -vvv` | Очень verbose |
| `ansible-vault encrypt file.yml` | Зашифровать файл |
| `ansible-vault edit file.yml` | Редактировать зашифрованный |
| `ansible-galaxy init role` | Создать структуру роли |
| `molecule test` | Тестировать роль |

# Приложение B: Готовые конфиги

## ansible.cfg

```ini
[defaults]
inventory = inventory/hosts.yml
remote_user = deploy
private_key_file = ~/.ssh/id_ed25519
host_key_checking = False

[privilege_escalation]
become = True
become_method = sudo
```

## site.yml — базовая настройка

```yaml
- hosts: all
  become: true
  roles:
    - common

- hosts: web
  become: true
  roles:
    - nginx
    - myapp
```

# Приложение C: Диагностика

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `UNREACHABLE` | SSH не работает | Проверь ключ, IP, порт 22 |
| `FAILED: sudo` | Нет sudo | Добавь `-b` или `become: true` |
| Не идемпотентно | Использован shell | Используй модуль (apt, service) |
| Template ошибка | Синтаксис Jinja2 | Проверь `{{ }}`, имена переменных |
| Vault ошибка | Неправильный пароль | Проверь `--vault-password-file` |
