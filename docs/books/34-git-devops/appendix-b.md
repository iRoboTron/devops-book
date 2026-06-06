# Приложение B: Типичные ошибки и как исправить

## «Закоммитил не в ту ветку»

**Ситуация:** сделал коммит в `main` вместо `feature/my-thing`.

```bash
# Шаг 1: запомни хеш коммита
git log --oneline -1
# abc1234 Мой коммит

# Шаг 2: создай ветку из текущего состояния
git switch -c feature/my-thing

# Шаг 3: вернись в main и отмени коммит
git switch main
git reset --hard HEAD~1
# Теперь main без лишнего коммита, feature/my-thing с ним
```

---

## «Забыл добавить файл в последний коммит»

**Ситуация:** только что закоммитил, но забыл добавить `config.yaml`.

Если коммит **ещё не запушен**:

```bash
git add config.yaml
git commit --amend --no-edit
# Коммит обновится без изменения сообщения
```

Если коммит **уже запушен**:

```bash
git add config.yaml
git commit -m "Добавить config.yaml (забыл в прошлом коммите)"
# Создать отдельный коммит — amend опасен для публичных веток
```

---

## «Написал плохое сообщение коммита»

Если коммит **не запушен**:

```bash
git commit --amend
# Откроется редактор — исправь сообщение
```

Если уже запушен — `git revert` и новый коммит с правильным сообщением. Либо смириться — не переписывай публичную историю.

---

## «Случайно запушил секрет»

**Это серьёзно.** Даже если удалишь файл — он останется в истории Git.

```bash
# Шаг 1: немедленно отозви/смени все скомпрометированные секреты
# API ключи, пароли, токены — меняй прямо сейчас

# Шаг 2: удали файл из истории (если репозиторий приватный и только ты)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/secret.env' \
  --prune-empty --tag-name-filter cat -- --all

# Современный способ (pip install git-filter-repo)
git filter-repo --path secret.env --invert-paths

# Шаг 3: force push (разрушает историю для всей команды!)
git push origin --force --all

# Шаг 4: добавить файл в .gitignore
echo "secret.env" >> .gitignore
git add .gitignore && git commit -m "Добавить secret.env в .gitignore"
```

> **Правило:** если репозиторий публичный — всё что попало в Git считается скомпрометированным. Удаление из истории не помогает: GitHub сохраняет кэши, могли сделать fork, могли уже сохранить секрет.

---

## «Detached HEAD — что это»

```bash
git checkout abc1234
# HEAD detached at abc1234
```

HEAD указывает не на ветку, а прямо на коммит. Новые коммиты «подвиснут в воздухе».

**Если нужно работать в этом состоянии:**

```bash
# Создать ветку из текущей позиции
git switch -c new-branch-name
```

**Если случайно попал и хочешь выйти:**

```bash
git switch main
# (потеряешь незакоммиченные изменения в detached состоянии)
```

**Если уже сделал коммиты в detached HEAD и хочешь их сохранить:**

```bash
# Запомни хеши коммитов через git log
git switch -c recovery-branch
# Теперь коммиты принадлежат ветке recovery-branch
```

---

## «Случайно удалил ветку»

```bash
git branch -D feature/my-thing
# Deleted branch feature/my-thing (was abc1234).
```

Восстановить через reflog:

```bash
git reflog
# abc1234 HEAD@{3}: commit: Мой коммит
# (найди нужный хеш)

git switch -c feature/my-thing abc1234
# Ветка восстановлена
```

---

## «Случайно сделал git reset --hard»

```bash
# Открой reflog — он помнит всё за ~30 дней
git reflog
# 9e8d7f6 HEAD@{0}: reset: moving to HEAD~3
# f1a2b3c HEAD@{1}: commit: Важный коммит
# a1b2c3d HEAD@{2}: commit: Ещё коммит

# Восстановить состояние до сброса
git reset --hard f1a2b3c
```

---

## «git push rejected — non-fast-forward»

```bash
git push
# ! [rejected]  main -> main (non-fast-forward)
```

На remote есть коммиты которых нет у тебя.

```bash
# Безопасный вариант: rebase поверх remote
git pull --rebase origin main
git push

# Если уверен что твои изменения важнее (ОПАСНО для shared ветки)
git push --force-with-lease origin feature/my-branch
# --force-with-lease безопаснее чем --force: не затирает чужие коммиты
```

---

## «Не могу переключить ветку — uncommitted changes»

```bash
git switch main
# error: Your local changes to the following files would be overwritten by checkout
```

```bash
# Вариант 1: сохранить изменения временно
git stash
git switch main
# ... делаем что нужно ...
git switch back-to-my-branch
git stash pop

# Вариант 2: закоммитить
git commit -am "WIP: не закончено"
git switch main

# Вариант 3: выбросить изменения (необратимо!)
git restore .
git switch main
```

---

## «Объединить последние N коммитов»

Перед пушем хочу привести историю в порядок:

```bash
# Интерактивный rebase для последних 4 коммитов
git rebase -i HEAD~4
# В редакторе: первый pick, остальные squash (или fixup)
# Сохранить и закрыть — Git предложит написать итоговое сообщение
```

---

## «Как найти в какой коммит попал баг»

`git bisect` делает бинарный поиск по истории:

```bash
git bisect start

# Пометить что в текущем коммите баг есть
git bisect bad

# Пометить коммит где баг точно не был (например, версия месяц назад)
git bisect good abc1234

# Git переключит на средний коммит — проверяй и говори bad/good
git bisect good   # если в этом коммите всё ОК
git bisect bad    # если баг уже есть

# Git сужает диапазон, пока не найдёт первый "плохой" коммит
# По завершении:
git bisect reset   # вернуться в исходное состояние
```
