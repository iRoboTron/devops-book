# Глава 1: Установка и первоначальная настройка

## Что вы узнаете

- как установить Git на Ubuntu/Debian и macOS;
- какие параметры нужно настроить перед первым использованием;
- где хранится конфигурация и как её посмотреть;
- как настроить удобный редактор и цветной вывод.

---

## Установка

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install git -y
git --version
# git version 2.43.0
```

Версия важна: Git активно развивается, и некоторые удобные флаги появились только в последних версиях. Для работы нужна минимум 2.28+ (defaultBranch). Предпочтительно 2.39+.

Если нужна свежая версия:

```bash
sudo add-apt-repository ppa:git-core/ppa
sudo apt update && sudo apt install git -y
```

### macOS

```bash
# через Homebrew
brew install git
```

Или через Xcode Command Line Tools: `xcode-select --install` — Git входит в комплект.

### Windows (WSL)

Если работаешь в WSL (Windows Subsystem for Linux) — используй Git внутри WSL:

```bash
sudo apt install git -y
```

Не устанавливай Git только для Windows и потом пытайся использовать его в WSL — это создаст путаницу с путями и переносами строк.

---

## Первоначальная настройка

Git привязывает каждый коммит к автору. Без настройки имени и email первый коммит завершится ошибкой.

```bash
git config --global user.name "Иван Петров"
git config --global user.email "ivan@example.com"
```

Флаг `--global` означает: эти настройки действуют для всех репозиториев на этой машине. Можно переопределить локально для конкретного репозитория (`--local` или просто без флага внутри репозитория).

### Ветка по умолчанию

Исторически Git создавал ветку `master`. Современное соглашение — `main`. Настроим чтобы `git init` всегда создавал `main`:

```bash
git config --global init.defaultBranch main
```

### Редактор

Git открывает текстовый редактор при написании длинного сообщения коммита, при interactive rebase и других операциях. По умолчанию — `vi` или `nano` в зависимости от системы.

```bash
# nano — проще для начинающих
git config --global core.editor nano

# vim
git config --global core.editor vim

# VS Code (открывает как вкладку и ждёт закрытия)
git config --global core.editor "code --wait"
```

### Окончания строк

На Linux/macOS — оставляем как есть:

```bash
git config --global core.autocrlf input
```

Это говорит Git: если файл пришёл с Windows-переносами (`\r\n`) — при добавлении в индекс конвертировать в Unix (`\n`). Обратно не трогать.

---

## Где хранится конфигурация

Git использует три уровня конфигурации:

```text
Уровень        Файл                         Область применения
──────────────────────────────────────────────────────────────────
system         /etc/gitconfig               все пользователи
global         ~/.gitconfig                 текущий пользователь
local          .git/config (в репозитории)  только этот репозиторий
```

Более конкретный уровень перекрывает менее конкретный: local > global > system.

Посмотреть все настройки и откуда они взяты:

```bash
git config --list --show-origin
```

Посмотреть конкретный параметр:

```bash
git config user.email
# ivan@example.com

git config --show-origin user.email
# file:/home/ivan/.gitconfig    ivan@example.com
```

Открыть глобальный конфиг в редакторе:

```bash
git config --global --edit
```

---

## Пример ~/.gitconfig после базовой настройки

```ini
[user]
    name = Иван Петров
    email = ivan@example.com

[init]
    defaultBranch = main

[core]
    editor = nano
    autocrlf = input

[color]
    ui = auto
```

`color.ui = auto` включает цветной вывод в терминале (ветки, изменения, статусы). Без него вывод монохромный.

---

## Полезные настройки сразу

### Сокращённый вывод статуса

```bash
git config --global status.short true
```

Вместо многословного `git status` будет компактный:

```
M  nginx.conf
?? new-script.sh
```

### Автоматический push в upstream

```bash
git config --global push.autoSetupRemote true
```

Без этого при первом `git push` новой ветки нужно писать `git push -u origin branch-name`. С этой настройкой — просто `git push`.

Доступно с Git 2.37+.

### Сохранение учётных данных (только HTTPS)

```bash
git config --global credential.helper store
```

Сохраняет логин/пароль в `~/.git-credentials` в открытом виде. Удобно на личной машине, не рекомендуется на shared-серверах. Более безопасный вариант — SSH-ключи (Глава 10).

---

## Проверка настройки

```bash
git config --list
# user.name=Иван Петров
# user.email=ivan@example.com
# init.defaultbranch=main
# core.editor=nano
# color.ui=auto
```

Если всё на месте — можно работать.

---

## Чек-лист для самопроверки

- [ ] Git установлен и `git --version` показывает 2.28+
- [ ] Настроены `user.name` и `user.email`
- [ ] `init.defaultBranch` установлен в `main`
- [ ] Выбран удобный редактор
- [ ] Понимаю разницу между `--system`, `--global` и `--local`

## Попробуйте сами

1. Установите Git и запустите `git config --list --show-origin`. Какие настройки уже есть по умолчанию и откуда?
2. Настройте имя, email, редактор и ветку по умолчанию. Откройте `~/.gitconfig` в текстовом редакторе — посмотрите что туда записалось.
3. Попробуйте `git config --global core.pager "less -F -X"` — это отключает пагинацию для коротких выводов. Запустите `git log` в маленьком репозитории — есть ли разница?
