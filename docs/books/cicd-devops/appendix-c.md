# Приложение C: Диагностика пайплайнов

---

## C.1 Job не запускается

### Симптом

Workflow висит на "Waiting" или "Queued".

### Причины

| Причина | Решение |
|---------|---------|
| Нет free runners | Подожди или используй self-hosted |
| Неправильный `on:` | Проверь триггер и ветку |
| Repository disabled | Settings → Actions → Enabled |

---

## C.2 `Permission denied` при docker push

### Симптом

```
denied: permission denied
```

### Решение

```yaml
# Убедись что GITHUB_TOKEN используется
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

# Проверь permissions в workflow
permissions:
  contents: read
  packages: write
```

GitHub → Settings → Actions → General → Workflow permissions:
✅ "Read and write permissions"

---

## C.3 SSH: `Host key verification failed`

### Симптом

```
Host key verification failed.
```

### Решение

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.SERVER_HOST }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    # Добавь:
    envs: GITHUB_SHA
    script: |
      ...
```

Или отключи проверку (только для CI):

```yaml
with:
  ...
  script: |
    export SSH_KNOWN_HOSTS=/dev/null
    ...
```

Или добавь fingerprint сервера:

```yaml
- name: Add server to known_hosts
  run: |
    mkdir -p ~/.ssh
    ssh-keyscan ${{ secrets.SERVER_HOST }} >> ~/.ssh/known_hosts
```

---

## C.4 Деплой прошёл, сайт не обновился

### Диагностика

```bash
# На сервере
ssh deploy@server

# 1. Правильный тег?
cat /opt/myapp/.env.deploy

# 2. Правильный образ?
docker compose config | grep image

# 3. Контейнер запущен?
docker compose ps

# 4. Логи контейнера?
docker compose logs app

# 5. Health check?
curl http://localhost:8000/health
```

### Частые причины

| Причина | Решение |
|---------|---------|
| IMAGE_TAG не обновился | Проверь workflow, `.env.deploy` |
| compose не pull | Добавь `docker compose pull` перед `up` |
| Старый образ закэширован | `docker compose down && docker compose up` |
| Nginx кеширует ответ | Очисти кэш Nginx |

---

## C.5 Пайплайн медленный

### Диагностика

В интерфейсе GitHub Actions посмотри время каждого шага.

### Решение

| Проблема | Решение |
|----------|---------|
| pip install каждый раз | `cache: 'pip'` в setup-python |
| Docker сборка с нуля | `cache-from: type=gha, cache-to: type=gha` |
| Много тестов | Параллельные job через matrix |
| Ненужные шаги | Убери лишнее из workflow |
| checkout слишком долгий | `fetch-depth: 1` (только последний коммит) |

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 1    # не качать всю историю
```

---

## C.6 Секреты попали в логи

### Симптом

В логах видно значение секрета вместо `***`.

### Решение

1. **Немедленно** отзови секрет (поменяй пароль, перегенерируй ключ)
2. Обнови секрет в GitHub
3. Никогда не `echo` секреты

```yaml
# Плохо
- run: echo ${{ secrets.SSH_KEY }}

# Хорошо
- run: echo "Secret is configured"
```

---

## C.7 `needs:` job не запускается

### Симптом

Job горит серым "Skipped".

### Причины

| Причина | Решение |
|---------|---------|
| Зависимый job упал | Почини зависимый job |
| Зависимый job skipped | Проверь цепочку `needs:` |
| `if:` условие не выполнено | Проверь условия |

### Цепочка

```
test (❌ failed)
  └── build (skipped)
        └── deploy (skipped)
```

---

## C.8 Dockerfile не найден при сборке

### Симптом

```
failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

### Решение

```yaml
# Dockerfile в корне
- uses: docker/build-push-action@v5
  with:
    context: .

# Dockerfile в поддиректории
- uses: docker/build-push-action@v5
  with:
    context: ./docker
    file: ./docker/Dockerfile.prod
```
