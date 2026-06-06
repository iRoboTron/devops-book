# Приложение C: Конфиг и алиасы

## Полный рекомендуемый ~/.gitconfig

```ini
[user]
    name = Твоё Имя
    email = email@example.com

[init]
    defaultBranch = main

[core]
    editor = nano
    autocrlf = input
    pager = less -F -X   # не запускать pager для коротких выводов

[color]
    ui = auto

[pull]
    rebase = true        # git pull всегда делает rebase, не merge

[push]
    autoSetupRemote = true   # не нужно -u при первом push

[rebase]
    autoStash = true     # автоматически stash/unstash при rebase

[merge]
    conflictstyle = diff3    # показывает оба изменения + общий предок

[diff]
    algorithm = histogram    # более умный алгоритм diff

[fetch]
    prune = true         # удалять локальные ссылки на удалённые ветки при fetch

[log]
    date = relative      # показывать "2 days ago" вместо абсолютного времени

[alias]
    # Компактный лог с графом
    lg = log --oneline --graph --decorate --all

    # Статус коротко
    st = status -s

    # Последний коммит
    last = log -1 HEAD --stat

    # Что готово к коммиту
    staged = diff --staged

    # Список всех веток с последним коммитом
    br = branch -vv

    # Отменить последний коммит (мягко — изменения остаются)
    undo = reset --soft HEAD~1

    # Показать все алиасы
    aliases = config --get-regexp '^alias\.'

    # Интерактивный rebase для N последних коммитов
    # Использование: git squash 3
    squash = "!f() { git rebase -i HEAD~$1; }; f"

    # Удалить все слитые ветки кроме main и develop
    cleanup = "!git branch --merged main | grep -v 'main\\|develop\\|\\*' | xargs git branch -d"

    # Быстрый коммит всего
    ca = commit -a -m

    # Посмотреть файл в конкретном коммите
    # Использование: git peek abc1234 file.txt  
    peek = "!f() { git show $1:$2; }; f"
```

---

## Настройка diff и merge инструментов

### VS Code как diff tool

```bash
git config --global diff.tool vscode
git config --global difftool.vscode.cmd 'code --wait --diff $LOCAL $REMOTE'
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait $MERGED'
```

Использование:

```bash
git difftool HEAD~1     # открыть diff в VS Code
git mergetool           # открыть конфликт в VS Code
```

### Vimdiff (если предпочитаешь терминал)

```bash
git config --global merge.tool vimdiff
git config --global mergetool.vimdiff.layout "LOCAL,BASE,REMOTE / MERGED"
```

---

## ~/.ssh/config для работы с несколькими аккаунтами

```text
# Личный GitHub
Host github-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_personal
    AddKeysToAgent yes

# Рабочий GitHub
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_work
    AddKeysToAgent yes

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519_gitlab
    AddKeysToAgent yes

# GitHub через порт 443 (если 22 заблокирован)
Host github.com
    HostName ssh.github.com
    User git
    Port 443
    IdentityFile ~/.ssh/id_ed25519
```

---

## Глобальный .gitignore_global

```bash
git config --global core.excludesFile ~/.gitignore_global
```

```gitignore
# macOS
.DS_Store
.AppleDouble
.LSOverride
._*

# Linux
*~
.fuse_hidden*
.Trash-*

# Editors
.idea/
.vscode/
*.swp
*.swo
*~
.project
.classpath

# Environments
.env
.env.local

# Временные файлы
*.tmp
*.bak
*.orig
```

---

## Полезные скрипты для .bashrc / .zshrc

```bash
# Текущая ветка в промпте (если нет Oh My Zsh / p10k)
parse_git_branch() {
    git branch 2>/dev/null | grep '^*' | colrm 1 2
}
PS1='\u@\h:\w $(parse_git_branch)$ '

# Быстрые функции
gac() {
    # git add all + commit
    git add . && git commit -m "$1"
}

gacp() {
    # git add all + commit + push
    git add . && git commit -m "$1" && git push
}

gnew() {
    # создать ветку и переключиться
    git switch -c "$1"
}
```

---

## .pre-commit-config.yaml — базовый шаблон

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: detect-private-key
      - id: no-commit-to-branch
        args: ['--branch', 'main', '--branch', 'master']

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
        # обнаружение секретов в коммите
```

Установить:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # проверить весь репозиторий сразу
```
