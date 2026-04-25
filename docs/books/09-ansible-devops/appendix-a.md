# Приложение A: Шпаргалка команд

| Команда | Назначение |
|---------|-----------|
| `ansible all -m ping` | Проверить подключение |
| `ansible web -m setup` | Получить факты хоста |
| `ansible web -m command -a "df -h /"` | Проверить свободное место |
| `ansible web -m command -a "ss -tulpn"` | Посмотреть открытые порты |
| `ansible-playbook site.yml` | Запустить playbook |
| `ansible-playbook site.yml --check --diff` | Dry-run с diff |
| `ansible-playbook site.yml --limit web1` | Запустить только для одного хоста |
| `ansible-playbook site.yml --tags deploy` | Запустить только часть playbook |
| `ansible-playbook site.yml --ask-vault-pass` | Запустить с vault-паролем |
| `ansible-vault encrypt file.yml` | Зашифровать файл |
| `ansible-vault encrypt_string 'value' --name 'var_name'` | Зашифровать одно значение |
| `ansible-galaxy install geerlingguy.nginx` | Установить роль из Galaxy |
| `molecule test` | Протестировать роль |

### Быстрый набор

```bash
# Проверка подключения
ansible all -m ping

# Запустить playbook
ansible-playbook site.yml

# Dry-run с diff
ansible-playbook site.yml --check --diff

# Только для одного хоста
ansible-playbook site.yml --limit web1

# С тегом
ansible-playbook site.yml --tags deploy

# С vault-паролем
ansible-playbook site.yml --ask-vault-pass

# Зашифровать значение
ansible-vault encrypt_string 'value' --name 'var_name'

# Посмотреть факты хоста
ansible web -m setup

# Установить роль из Galaxy
ansible-galaxy install geerlingguy.nginx
```

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
| `changed > 0` на втором запуске | Задача неидемпотентна | Ищи `shell`, случайный вывод, права файла |
| Сервис не стартует после деплоя | Ошибка конфига или приложения | Проверь `systemctl status` и `journalctl` |
