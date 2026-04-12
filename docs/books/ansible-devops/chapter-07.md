# Глава 7: Vault — шифрование секретов

> **Запомни:** Секреты в git = секрет для всех. Vault шифрует — можно коммитить зашифрованное.

---

## 7.1 Проблема

```yaml
# group_vars/all.yml ← в git
db_password: supersecret123    # ❌ все видят
```

---

## 7.2 Создать зашифрованный файл

```bash
ansible-vault encrypt group_vars/all/secrets.yml
```

Теперь файл зашифрован. Содержимое нечитаемо.

### Редактировать

```bash
ansible-vault edit group_vars/all/secrets.yml
```

Откроет редактор → сохрани → снова зашифрован.

### Посмотреть

```bash
ansible-vault view group_vars/all/secrets.yml
```

---

## 7.3 Запустить playbook

```bash
ansible-playbook site.yml --ask-vault-pass
# Введи пароль
```

Или через файл пароля:

```bash
echo "my-vault-password" > .vault_pass
chmod 600 .vault_pass

ansible-playbook site.yml --vault-password-file .vault_pass
```

> **Опасно:** `.vault_pass` ВСЕГДА в `.gitignore`.
> Зашифрованные файлы — МОЖНО коммитить.

---

## 7.4 В CI

```yaml
- name: Run playbook
  run: ansible-playbook site.yml --vault-password-file /tmp/vault_pass
  env:
    ANSIBLE_VAULT_PASSWORD_FILE: ${{ secrets.VAULT_PASS }}
```

---

## 📝 Упражнения

### Упражнение 7.1: Зашифровать
**Задача:**
1. Создай файл с секретом
2. `ansible-vault encrypt` — зашифрован?
3. `ansible-vault view` — можешь прочитать?
4. `ansible-playbook --ask-vault-pass` — работает?

---

## 📋 Чеклист главы 7

- [ ] Я могу зашифровать файл через `ansible-vault encrypt`
- [ ] Я могу редактировать зашифрованный файл
- [ ] Я запускаю playbook с `--ask-vault-pass`
- [ ] `.vault_pass` в `.gitignore`

**Всё отметил?** Переходи к Главе 8 — Loops и conditions.
