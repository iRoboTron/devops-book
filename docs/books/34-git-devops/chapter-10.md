# Глава 10: SSH-ключи и работа с GitHub/GitLab

## Что вы узнаете

- чем SSH лучше HTTPS для работы с репозиториями;
- как сгенерировать SSH-ключ и добавить его на GitHub/GitLab;
- как настроить несколько ключей для разных аккаунтов;
- Personal Access Tokens как альтернатива SSH.

---

## HTTPS vs SSH

```text
HTTPS:
git clone https://github.com/user/repo.git
+ Работает везде (даже за строгим корпоративным файрволом)
- Нужно вводить логин/пароль (или токен) при каждой операции
- Токен нужно хранить безопасно

SSH:
git clone git@github.com:user/repo.git
+ Аутентификация автоматическая после первой настройки
+ Приватный ключ никогда не покидает твою машину
- Порт 22 может быть заблокирован (решается через порт 443)
```

Для ежедневной работы SSH удобнее — нет паролей, всё работает автоматически.

---

## Генерация SSH-ключа

```bash
# Современный алгоритм ed25519 (рекомендуется)
ssh-keygen -t ed25519 -C "your.email@example.com"

# Если сервер не поддерживает ed25519 — RSA 4096 бит
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"
```

Вывод:

```
Generating public/private ed25519 key pair.
Enter file in which to save the key (/home/ivan/.ssh/id_ed25519):
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
```

- Путь к ключу: нажми Enter для стандартного `~/.ssh/id_ed25519`
- Passphrase: опционально, но рекомендуется. Защищает ключ если файл попадёт к злоумышленнику.

После генерации:

```bash
ls ~/.ssh/
# id_ed25519       ← приватный ключ (никому не давать!)
# id_ed25519.pub   ← публичный ключ (можно везде публиковать)
```

---

## Добавить ключ на GitHub

```bash
# Скопировать публичный ключ в буфер обмена
cat ~/.ssh/id_ed25519.pub
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... your.email@example.com
```

На GitHub:
1. Settings → SSH and GPG keys → New SSH key
2. Title: название (например «Рабочий ноутбук»)
3. Key: вставить содержимое `id_ed25519.pub`
4. Add SSH key

Проверить подключение:

```bash
ssh -T git@github.com
# Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## Добавить ключ на GitLab

Аналогично GitHub:

1. User Settings → SSH Keys → Add new key
2. Вставить содержимое `id_ed25519.pub`

Проверить:

```bash
ssh -T git@gitlab.com
# Welcome to GitLab, @username!
```

---

## Несколько SSH-ключей для разных аккаунтов

Ситуация: личный GitHub и рабочий GitLab на одной машине, разные аккаунты.

### Генерируем отдельные ключи

```bash
# Личный GitHub
ssh-keygen -t ed25519 -C "personal@gmail.com" -f ~/.ssh/id_ed25519_github_personal

# Рабочий GitLab
ssh-keygen -t ed25519 -C "work@company.com" -f ~/.ssh/id_ed25519_gitlab_work
```

### Конфигурируем ~/.ssh/config

```bash
nano ~/.ssh/config
```

```text
# Личный GitHub
Host github-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_personal

# Рабочий GitLab
Host gitlab-work
    HostName gitlab.company.com
    User git
    IdentityFile ~/.ssh/id_ed25519_gitlab_work
```

### Использование

```bash
# Клонировать через личный аккаунт
git clone github-personal:myusername/my-repo.git
# (вместо git@github.com:myusername/my-repo.git)

# Клонировать через рабочий аккаунт
git clone gitlab-work:company/project.git

# Проверить
ssh -T github-personal
ssh -T gitlab-work
```

---

## SSH-агент — не вводить passphrase каждый раз

Если задал passphrase при генерации ключа — SSH-агент запомнит его до конца сессии:

```bash
# Запустить агент (обычно уже запущен)
eval "$(ssh-agent -s)"

# Добавить ключ в агент
ssh-add ~/.ssh/id_ed25519
# Enter passphrase for /home/ivan/.ssh/id_ed25519:
# Identity added: /home/ivan/.ssh/id_ed25519

# Список добавленных ключей
ssh-add -l
```

На macOS ключи автоматически добавляются в Keychain при добавлении в агент.

---

## Personal Access Token (PAT) — альтернатива SSH

Если SSH заблокирован или нужен токен для скриптов:

**GitHub:**
1. Settings → Developer Settings → Personal Access Tokens → Tokens (classic) → Generate new token
2. Выбрать права: `repo` (полный доступ к приватным репозиториям)
3. Скопировать токен — **больше не покажут**

**Использование:**

```bash
# При HTTPS аутентификации вместо пароля — вводить токен
git clone https://github.com/user/repo.git
# Username: your-username
# Password: ghp_xxxxxxxxxxxx  ← токен, не пароль

# Или прямо в URL (не для production, только для автоматизации)
git clone https://token:ghp_xxxxxxxxxxxx@github.com/user/repo.git
```

**Хранение токена в `~/.netrc`:**

```text
machine github.com
  login your-username
  password ghp_xxxxxxxxxxxx
```

```bash
chmod 600 ~/.netrc
```

---

## SSH через порт 443

Если порт 22 заблокирован корпоративным файрволом:

```text
# ~/.ssh/config
Host github.com
    HostName ssh.github.com
    User git
    Port 443
    IdentityFile ~/.ssh/id_ed25519
```

GitHub и GitLab поддерживают SSH на порту 443.

---

## Чек-лист для самопроверки

- [ ] Понимаю разницу между приватным и публичным ключом
- [ ] Умею сгенерировать ed25519 ключ и добавить на GitHub/GitLab
- [ ] Знаю как настроить `~/.ssh/config` для нескольких аккаунтов
- [ ] Умею проверить SSH-соединение через `ssh -T`
- [ ] Знаю что такое PAT и когда он нужен вместо SSH

## Попробуйте сами

1. Сгенерируйте SSH-ключ ed25519 и добавьте его на GitHub. Склонируйте любой свой репозиторий через SSH (`git@github.com:...`). Убедитесь что работает без пароля.
2. Если у вас два аккаунта (личный и рабочий), настройте `~/.ssh/config` с двумя хостами. Проверьте оба через `ssh -T`.
3. Сгенерируйте Personal Access Token на GitHub с правами `repo`. Попробуйте использовать его для HTTPS-клонирования.
