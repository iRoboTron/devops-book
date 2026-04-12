# Глава 5: Секреты и переменные окружения

> **Запомни:** Секреты в коде = секреты для всего мира. GitHub Secrets — безопасный способ передать ключи в пайплайн.

---

## 5.1 Проблема: где хранить ключи

### Плохо

```yaml
# .github/workflows/deploy.yml
- uses: appleboy/ssh-action@v1
  with:
    host: 203.0.113.50
    username: deploy
    key: |
      -----BEGIN RSA PRIVATE KEY-----
      MIIEpAIBAAKCAQEA...    ← SSH КЛЮЧ В ФАЙЛЕ!
      ...
```

**Проблемы:**
- Ключ в репозитории → любой с доступом видит
- Ключ в истории git → даже если удалить, остаётся
- Ключ в логах Actions → видно всем кто видит workflow

### Хорошо

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.SERVER_HOST }}
    username: deploy
    key: ${{ secrets.SSH_PRIVATE_KEY }}
```

Секреты в специальном хранилище GitHub. Не в файлах.

---

## 5.2 GitHub Secrets: где и как

### Создать секрет

GitHub → Settings → **Secrets and variables** → **Actions** → **New repository secret**:

```
Name:  SERVER_HOST
Value: 203.0.113.50

Name:  SSH_PRIVATE_KEY
Value: (содержимое id_ed25519)
```

### Использовать в workflow

```yaml
steps:
  - uses: appleboy/ssh-action@v1
    with:
      host: ${{ secrets.SERVER_HOST }}
      key: ${{ secrets.SSH_PRIVATE_KEY }}
```

### Как это работает

```
Workflow запускается
    │
    │  ${{ secrets.SERVER_HOST }}
    │        ↓
    │  GitHub подставляет значение
    │        ↓
    │  appleboy/ssh-action получает "203.0.113.50"
    │
    ▼
  Команда выполняется
```

Секрет **никогда** не появляется в файле или логах.

> **Запомни:** GitHub маскирует секреты в логах.
> Даже если ты сделаешь `echo ${{ secrets.X }}` — увидишь `***`.
> Но не проверяй это намеренно.

---

## 5.3 Variables vs Secrets

| | Secrets | Variables |
|--|---------|-----------|
| **Видны в UI** | ❌ (только имя) | ✅ |
| **В логах** | `***` (замаскированы) | Видны |
| **Для чего** | Пароли, ключи, токены | URL, имена, флаги |
| **Пример** | `SSH_PRIVATE_KEY` | `SERVER_URL` |

### Когда что использовать

```yaml
# Variable — не секрет
env:
  IMAGE_NAME: ghcr.io/${{ github.repository }}

# Secret — пароль
env:
  SSH_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
```

### Создать Variable

GitHub → Settings → Secrets and variables → Actions → **Variables** → **New repository variable**:

```
Name:  SERVER_URL
Value: https://myapp.ru
```

В workflow:

```yaml
- run: curl ${{ vars.SERVER_URL }}/health
```

> **Запомни:** `${{ vars.X }}` для переменных.
> `${{ secrets.X }}` для секретов.

---

## 5.4 Переменные окружения в workflow

### Глобальные для всех jobs

```yaml
env:
  IMAGE_NAME: myapp
  REGISTRY: ghcr.io

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo $IMAGE_NAME      # myapp
      - run: echo $REGISTRY        # ghcr.io
```

### Для конкретного job

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      IMAGE_TAG: latest
    steps:
      - run: echo $IMAGE_TAG       # latest
```

### Для конкретного шага

```yaml
    steps:
      - run: echo $MY_VAR
        env:
          MY_VAR: hello            # только в этом шаге
```

---

## 5.5 Контекст `github.*`

GitHub автоматически подставляет информацию о событии.

```yaml
steps:
  - run: echo "SHA: ${{ github.sha }}"
  - run: echo "Branch: ${{ github.ref_name }}"
  - run: echo "Actor: ${{ github.actor }}"
  - run: echo "Event: ${{ github.event_name }}"
```

| Переменная | Значение | Пример |
|-----------|----------|--------|
| `github.sha` | Хэш коммита | `abc123def456...` |
| `github.ref_name` | Имя ветки | `main` |
| `github.actor` | Кто запушил | `adelfos` |
| `github.event_name` | Тип события | `push` |
| `github.repository` | Репозиторий | `adelfos/myapp` |
| `github.workspace` | Путь к коду | `/home/runner/work/myapp/myapp` |

### Зачем `github.sha` для деплоя

```yaml
- run: echo "IMAGE_TAG=${{ github.sha }}" >> .env.deploy
```

Каждый коммит = уникальный тег образа.
Можно откатиться к любому коммиту.

---

## 5.6 Environments: staging vs production

**Environment** — группа с отдельными секретами и правилами.

### Создать Environment

GitHub → Settings → Environments → **New environment**:

```
Name: production
✅ Required reviewers (нужно подтвердить)
✅ Wait timer: 5 min
```

### Использовать в workflow

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging          ← staging environment
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment: production       ← production environment
    steps:
      - run: echo "Deploying to production"
```

### Что даёт Environment

| Функция | Что делает |
|---------|-----------|
| Separate secrets | Свой `DATABASE_URL` для staging и production |
| Required reviewers | Кто-то должен подтвердить деплой |
| Wait timer | Подождать N минут перед запуском |
| Branch rules | Деплоить production только с `main` |

### В интерфейсе GitHub

```
Deploy production
  ⏳ Waiting for approval

[Approve] [Reject]
```

> **Совет:** Используй Environments когда есть staging и production.
> Для одного сервера — не нужно.

---

## 📝 Упражнения

### Упражнение 5.1: Создать секреты
**Задача:**
1. Создай секрет `TEST_SECRET` = "hello" в Settings → Secrets
2. Создай workflow:
   ```yaml
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - run: echo "Secret is set: ${{ secrets.TEST_SECRET != '' }}"
   ```
3. Запушь — секрет доступен?
4. Попробуй `echo ${{ secrets.TEST_SECRET }}` — видно значение? (должно быть ***)

### Упражнение 5.2: Variables
**Задача:**
1. Создай Variable `APP_NAME` = "myapp"
2. В workflow:
   ```yaml
   - run: echo "App: ${{ vars.APP_NAME }}"
   ```
3. Запушь — значение видно в логах? (да, это не секрет)

### Упражнение 5.3: github контекст
**Задача:**
1. Создай workflow который выводит:
   ```yaml
   - run: echo "SHA=${{ github.sha }}"
   - run: echo "Branch=${{ github.ref_name }}"
   - run: echo "By=${{ github.actor }}"
   ```
2. Запушь — правильные значения?

### Упражнение 5.4: Environment (если есть staging)
**Задача:**
1. Создай Environment `staging`
2. Добавь secret `DB_PASSWORD` для staging
3. Создай job с `environment: staging`
4. Запушь — job использует секрет из staging?

### Упражнение 5.5: DevOps Think
**Задача:** «Ты случайно добавил `echo ${{ secrets.SSH_KEY }}` в workflow. Ключ скомпрометирован?»

Ответ:
- GitHub маскирует секреты в логах (покажет ***)
- Но специально выводить секрет — плохая идея
- Если ключ реально попал в логи — считай скомпрометированным
- Решение: отзови ключ, создай новый, обнови секрет
- Урок: никогда не echo секрет, даже для "проверки"

---

## 📋 Чеклист главы 5

- [ ] Я понимаю почему нельзя хранить секреты в файлах
- [ ] Я могу создать GitHub Secret
- [ ] Я понимаю разницу Secrets vs Variables
- [ ] Я могу использовать `${{ secrets.X }}` в workflow
- [ ] Я могу настроить переменные окружения (глобально, job, step)
- [ ] Я знаю контекст `github.*` (sha, ref_name, actor)
- [ ] Я понимаю зачем Environments (staging/production)
- [ ] Я знаю что GitHub маскирует секреты в логах (***)

**Всё отметил?** Переходи к Главе 6 — сборка Docker-образа.
