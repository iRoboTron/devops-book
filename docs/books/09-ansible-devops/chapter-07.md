# Глава 7: Vault — шифрование секретов

> **Запомни:** Секреты в git = секрет для всех. Vault шифрует — можно коммитить зашифрованное.
>
> **Проект этой главы:** прячем `DB_PASSWORD` и `SECRET_KEY` для Flask-приложения.
> К концу книги: Flask-приложение за Nginx, деплой одной командой.

---

## 7.1 Проблема

Так хранить секреты нельзя:

```yaml
# group_vars/all.yml ← в git
db_password: supersecret123
secret_key: flask-dev-secret
```

Любой, у кого есть доступ к репозиторию, увидит пароль базы и секрет приложения.

---

## 7.2 Создать зашифрованный файл

```bash
ansible-vault encrypt group_vars/all/secrets.yml
```

Теперь файл зашифрован. Содержимое выглядит так:

```text
$ANSIBLE_VAULT;1.1;AES256
38313534363534386162623866613739363564653535303337623231333831656138356439626437
6165333631306561623664373362393262313464393135620a646561366465396234386439383662
...
```

Это безопасно коммитить в git: без vault-пароля файл не прочитать.

### Редактировать

```bash
ansible-vault edit group_vars/all/secrets.yml
```

Откроет редактор, после сохранения файл снова будет зашифрован.

### Посмотреть

```bash
ansible-vault view group_vars/all/secrets.yml
```

Внутри может лежать, например, такой YAML:

```yaml
db_password: SuperSecret123
secret_key: FlaskUltraSecretKey
```

---

## 7.3 Запустить playbook

Самый простой вариант:

```bash
ansible-playbook site.yml --ask-vault-pass
```

Ansible спросит пароль перед запуском.

Или через файл пароля:

```text
# .vault_pass
my-vault-password
```

```bash
chmod 600 .vault_pass
ansible-playbook site.yml --vault-password-file .vault_pass
```

> **Опасно:** `.vault_pass` ВСЕГДА в `.gitignore`.
> Зашифрованные файлы — МОЖНО коммитить. Файл с паролем — НИКОГДА.

---

## 7.4 В CI

В CI пароль обычно приходит из секрета платформы, а перед запуском временно пишется в файл:

```yaml
- name: Run playbook
  run: |
    printf '%s' "$VAULT_PASS" > /tmp/vault_pass
    chmod 600 /tmp/vault_pass
    ansible-playbook site.yml --vault-password-file /tmp/vault_pass
  env:
    VAULT_PASS: ${{ secrets.ANSIBLE_VAULT_PASS }}
```

Так секрет не хранится в репозитории, а playbook всё равно может прочитать vault.

---

## 7.5 Зашифровать одно значение (`vault_string`)

Часто не нужен целый зашифрованный файл. Иногда достаточно спрятать одно поле прямо в YAML:

```bash
ansible-vault encrypt_string 'SuperSecret123' --name 'db_password'
```

Вывод будет таким:

```yaml
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63386130663561616662386639613830...
```

Этот блок можно вставить прямо в `group_vars/all.yml` рядом с обычными переменными:

```yaml
app_port: 8000
domain: myapp.ru
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          63386130663561616662386639613830...
```

Так удобнее: обычные настройки читаемы, а секреты зашифрованы.

---

## 📝 Упражнения

### Упражнение 7.1: Зашифровать
**Задача:**
1. Создай файл `group_vars/all/secrets.yml` с `db_password` и `secret_key`
2. `ansible-vault encrypt group_vars/all/secrets.yml` — файл стал нечитаемым?
3. `ansible-vault view group_vars/all/secrets.yml` — пароль спрашивается?
4. Запусти `ansible-playbook site.yml --ask-vault-pass`
5. Попробуй `ansible-vault encrypt_string 'SuperSecret123' --name 'db_password'`

---

## 📋 Чеклист главы 7

- [ ] Я могу зашифровать файл через `ansible-vault encrypt`
- [ ] Я могу редактировать зашифрованный файл
- [ ] Я запускаю playbook с `--ask-vault-pass`
- [ ] `.vault_pass` в `.gitignore`

**Всё отметил?** Переходи к Главе 8 — Loops и conditions.
