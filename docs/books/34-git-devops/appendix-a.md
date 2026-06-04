# Приложение A: Шпаргалка команд

## Настройка

```bash
git config --global user.name "Имя Фамилия"
git config --global user.email "email@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global push.autoSetupRemote true
git config --global core.editor nano
git config --list --show-origin
```

## Создание репозитория

```bash
git init                           # инициализировать в текущей директории
git init project-name              # создать новую директорию
git clone git@github.com:u/r.git   # клонировать
git clone --depth 1 URL            # shallow clone (только последний коммит)
```

## Основные операции

```bash
git status                    # что происходит
git status -s                 # компактный вывод
git add file.txt              # добавить файл в индекс
git add .                     # добавить все изменения
git add -p file.txt           # интерактивно выбрать части файла
git commit -m "Сообщение"     # зафиксировать
git commit -a -m "Сообщение"  # add + commit для отслеживаемых файлов
git commit --amend            # изменить последний коммит (не запушенный!)
```

## Просмотр изменений

```bash
git diff                      # не в индексе
git diff --staged             # в индексе (готово к коммиту)
git diff HEAD~1               # относительно предыдущего коммита
git diff branch1..branch2     # разница между ветками
git show abc1234              # конкретный коммит
git show abc1234:file.txt     # файл в конкретном коммите
```

## История

```bash
git log                            # подробный лог
git log --oneline                  # одна строка на коммит
git log --oneline --graph --all    # граф всех веток
git log -5                         # последние 5 коммитов
git log --oneline file.txt         # история конкретного файла
git log --author="Ivan"            # фильтр по автору
git log --grep="nginx"             # фильтр по сообщению
git log -S "worker_connections"    # коммиты изменившие строку
git blame file.txt                 # кто менял каждую строку
```

## Ветки

```bash
git branch                   # список веток
git branch -v                # с последним коммитом
git branch -vv               # с tracking
git switch -c feature/name   # создать и переключиться
git switch branch-name       # переключиться
git branch -d feature/name   # удалить слитую ветку
git branch -D feature/name   # принудительно удалить
git branch --merged main     # ветки слитые в main
```

## Слияние и rebase

```bash
git merge feature/name           # слить в текущую ветку
git merge --no-ff feature/name   # всегда с merge commit
git merge --abort                # отменить слияние
git rebase main                  # перенести ветку на main
git rebase -i HEAD~3             # интерактивный rebase
git rebase --continue            # продолжить после разрешения конфликта
git rebase --abort               # отменить rebase
```

## Remote

```bash
git remote -v                           # список remotes
git remote add origin URL               # добавить remote
git remote set-url origin NEW_URL       # изменить URL
git fetch origin                        # загрузить без слияния
git pull                                # fetch + merge/rebase
git pull --rebase                       # fetch + rebase
git push                                # отправить
git push -u origin branch              # первый push с tracking
git push origin --delete branch        # удалить ветку на remote
git push origin --tags                 # запушить все теги
```

## Откаты

```bash
git restore file.txt              # отменить изменения в файле (необратимо!)
git restore --staged file.txt     # убрать из индекса
git reset --soft HEAD~1           # отменить коммит, оставить в индексе
git reset --mixed HEAD~1          # отменить коммит, оставить в рабочей директории
git reset --hard HEAD~1           # отменить коммит и изменения (необратимо!)
git revert abc1234                # создать коммит-откат (безопасно)
git cherry-pick abc1234           # взять коммит из другой ветки
```

## Stash

```bash
git stash                          # сохранить изменения
git stash push -m "Описание"       # с именем
git stash list                     # список
git stash pop                      # достать последний
git stash apply stash@{1}          # применить конкретный
git stash drop stash@{1}           # удалить конкретный
git stash clear                    # очистить всё
```

## Теги

```bash
git tag                          # список тегов
git tag v1.2.0                   # лёгкий тег
git tag -a v1.2.0 -m "Release"  # аннотированный тег
git push origin v1.2.0          # запушить тег
git push origin --tags          # запушить все теги
git tag -d v1.2.0               # удалить локально
git push origin --delete v1.2.0 # удалить на remote
```

## .gitignore

```bash
git rm --cached file.txt       # убрать из отслеживания (оставить на диске)
git rm --cached -r directory/  # рекурсивно
git check-ignore -v file.txt   # почему файл игнорируется
```

## Диагностика

```bash
git reflog                     # история всех перемещений HEAD
git fsck                       # проверить целостность репозитория
git gc                         # оптимизировать репозиторий
git rev-parse HEAD             # хеш текущего коммита
git rev-parse --short HEAD     # короткий хеш
git branch --show-current      # имя текущей ветки
git describe --tags            # ближайший тег + коммиты после
git status --porcelain         # машиночитаемый статус (для скриптов)
```
