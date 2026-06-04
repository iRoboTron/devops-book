# Глава 3: Базовые операции — add, commit, log, diff

## Что вы узнаете

- как создать репозиторий и сделать первый коммит;
- как читать вывод `git status` и `git diff`;
- как смотреть историю коммитов удобным способом;
- полезные флаги которые используются каждый день.

---

## Создание репозитория

```bash
# Новый репозиторий в текущей директории
git init

# Новый репозиторий в новой директории
git init my-project
cd my-project
```

После `git init` появится `.git/`. Репозиторий пустой — коммитов нет.

```bash
git status
# On branch main
#
# No commits yet
#
# nothing to commit (create/copy files and use "git add" to track)
```

---

## git status — что происходит

`git status` — самая часто используемая команда. Запускай её перед каждым `git add` и `git commit`.

```bash
# Создадим файлы
echo "worker_processes auto;" > nginx.conf
echo "#!/bin/bash" > deploy.sh

git status
# On branch main
#
# No commits yet
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#         deploy.sh
#         nginx.conf
#
# nothing added to commit but untracked files present
```

Статусы файлов:

| Статус | Означает |
|--------|----------|
| `Untracked` | Git не следит за этим файлом |
| `Modified` | Файл изменён, изменения не в индексе |
| `Staged` | Файл добавлен в индекс, ждёт коммита |
| `Deleted` | Файл удалён |

---

## git add — добавить в индекс

```bash
# Добавить конкретный файл
git add nginx.conf

# Добавить несколько файлов
git add nginx.conf deploy.sh

# Добавить все изменения в текущей директории
git add .

# Добавить изменения интерактивно (выбрать части файла)
git add -p nginx.conf
```

После `git add nginx.conf`:

```bash
git status
# Changes to be committed:
#   (use "git rm --cached <file>..." to unstage)
#         new file:   nginx.conf
#
# Untracked files:
#         deploy.sh
```

`nginx.conf` теперь в индексе (staged), `deploy.sh` — нет.

### git add -p — частичное добавление

Если файл содержит несколько несвязанных изменений, можно добавить только часть:

```bash
git add -p nginx.conf
```

Git покажет каждый «кусок» (hunk) изменений и спросит: добавить (`y`), пропустить (`n`), разбить мельче (`s`), редактировать вручную (`e`)?

---

## git commit — зафиксировать изменения

```bash
# Коммит с сообщением в командной строке
git commit -m "Добавить базовую конфигурацию nginx"

# Если нужно длинное сообщение — откроется редактор
git commit
```

После коммита:

```bash
git status
# On branch main
# nothing to commit, working tree clean
```

«Working tree clean» — всё зафиксировано, изменений нет.

### Коммит всех отслеживаемых изменений без add

```bash
git commit -a -m "Исправить опечатку"
```

`-a` добавляет в коммит изменения всех уже отслеживаемых файлов (не новых). Удобно для быстрых правок, но обходит контроль через индекс — используй осторожно.

### Хорошее сообщение коммита

```text
Плохо:
git commit -m "фикс"
git commit -m "изменения"
git commit -m "ещё раз"

Хорошо:
git commit -m "Увеличить worker_connections до 1024 для высокой нагрузки"
git commit -m "Добавить ретрай в скрипт деплоя: 3 попытки с паузой 5s"
git commit -m "Исправить ошибку 502 при больших загрузках файлов"
```

Правило: сообщение коммита должно объяснять **что и зачем**, а не «как» (код и так покажет «как»).

---

## git log — история коммитов

```bash
git log
# commit abc1234def5678...
# Author: Ivan Petrov <ivan@example.com>
# Date:   Mon Jun 2 14:30:00 2026 +0300
#
#     Добавить базовую конфигурацию nginx
```

По умолчанию — подробно. Полезные форматы:

```bash
# Компактно: одна строка на коммит
git log --oneline
# abc1234 Добавить базовую конфигурацию nginx
# 7e9d4a1 Исправить upstream в proxy_pass

# С графом веток
git log --oneline --graph --all

# Последние 5 коммитов
git log -5

# Коммиты конкретного файла
git log --oneline nginx.conf

# Коммиты конкретного автора
git log --author="Ivan"

# Коммиты за период
git log --since="2026-01-01" --until="2026-06-01"

# Поиск по тексту сообщения
git log --grep="nginx"
```

### Удобный алиас для log

Разбор формата подробнее в Приложении C, но вот сразу полезный алиас:

```bash
git config --global alias.lg "log --oneline --graph --decorate --all"
git lg
# * abc1234 (HEAD -> main) Добавить конфиг nginx
# * 7e9d4a1 Первоначальный коммит
```

---

## git diff — посмотреть изменения

```bash
# Изменения в рабочей директории (не добавленные в индекс)
git diff

# Изменения в индексе (добавленные, но не закоммиченные)
git diff --staged
# или
git diff --cached   # синонимы

# Разница между двумя коммитами
git diff abc1234 7e9d4a1

# Разница между ветками
git diff main feature/auth

# Разница для конкретного файла
git diff nginx.conf
```

Пример вывода `git diff`:

```diff
diff --git a/nginx.conf b/nginx.conf
index 3b2c8f0..a3f1b2c 100644
--- a/nginx.conf
+++ b/nginx.conf
@@ -1,5 +1,5 @@
 worker_processes auto;
-worker_connections 512;
+worker_connections 1024;
 
 http {
```

`-` — удалённая строка, `+` — добавленная, без символа — контекст без изменений.

---

## Полный цикл: создать → изменить → зафиксировать

```bash
# Инициализировать репозиторий
git init infra-configs
cd infra-configs

# Создать файл
cat > nginx.conf << 'EOF'
worker_processes auto;
worker_connections 512;

http {
    include mime.types;
}
EOF

# Добавить в индекс
git add nginx.conf

# Зафиксировать
git commit -m "Начальная конфигурация nginx"

# Изменить файл
sed -i 's/512/1024/' nginx.conf

# Посмотреть что изменилось
git diff

# Добавить и закоммитить
git add nginx.conf
git commit -m "Увеличить worker_connections до 1024"

# Посмотреть историю
git log --oneline
# abc1234 Увеличить worker_connections до 1024
# 7e9d4a1 Начальная конфигурация nginx
```

---

## git rm и git mv

```bash
# Удалить файл из репозитория и из диска
git rm old-config.conf

# Удалить из репозитория, но оставить на диске (unstage tracked file)
git rm --cached secret.env

# Переименовать файл
git mv nginx.conf nginx-prod.conf
```

`git mv` — это то же самое что `mv` + `git add` нового + `git rm` старого. Git отследит переименование.

---

## git restore — отменить изменения

```bash
# Отменить изменения в файле (вернуть к версии из HEAD)
git restore nginx.conf

# Убрать файл из индекса (unstage), не отменяя изменения
git restore --staged nginx.conf
```

> ☠️ **Осторожно:** `git restore nginx.conf` без `--staged` **необратимо** отбрасывает незакоммиченные изменения в файле. Отменить нельзя.

---

## Чек-лист для самопроверки

- [ ] Могу создать репозиторий и сделать первый коммит
- [ ] Понимаю вывод `git status` — untracked, modified, staged
- [ ] Знаю как добавить конкретные файлы и как добавить всё через `git add .`
- [ ] Умею смотреть историю через `git log --oneline`
- [ ] Понимаю вывод `git diff` — что значат `+` и `-`
- [ ] Знаю разницу между `git diff` и `git diff --staged`

## Попробуйте сами

1. Создайте репозиторий с тремя файлами. Сделайте `git add` только для одного, затем запустите `git status` — убедитесь что видно разницу между staged и untracked.
2. Измените один файл в двух разных местах (два разных блока). Запустите `git add -p` и добавьте только первое изменение. Сделайте коммит. Потом добавьте второе изменение и сделайте второй коммит. Проверьте через `git log --oneline`.
3. Настройте алиас `git lg` как показано выше. Сделайте несколько коммитов и запустите `git lg` — привыкайте к этому формату.
