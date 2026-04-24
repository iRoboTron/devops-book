# Глава 8: Стратегии деплоя

> **Запомни:** Простой деплой = даунтайм. Rolling update = почти без даунтайма. Rollback = быстрый откат если что-то пошло не так.

---

## 8.1 Проблема простого деплоя

```bash
docker compose down     ← 5-15 секунд сайт недоступен
docker compose up -d    ← пока контейнер запускается
```

Пользователь видит:

```
502 Bad Gateway
```

На 5-15 секунд. Для маленького проекта — ок. Для продакшена — нет.

---

## 8.2 Rolling update через docker-compose

Вместо `down` → `up`:

```bash
# 1. Скачать новый образ
docker compose pull app

# 2. Пересоздать только app (без down)
docker compose up -d --no-deps app
```

`--no-deps` = не перезапускать зависимости (БД, Redis).
Только app.

### Что происходит

```
Старый контейнер работает
         │
         │ docker compose up -d --no-deps app
         │
         ▼
Docker создаёт новый контейнер
         │
         │ Новый готов → старый удаляется
         │
         ▼
Новый контейнер работает

Даунтайм: 1-2 секунды (переключение)
```

> **Совет:** Используй `up -d --no-deps` вместо `down && up`.
> Меньше даунтайм, меньше рисков.

---

## 8.3 Healthcheck перед переключением

Что если новый код сломан? Контейнер запустился но приложение не работает.

```bash
docker compose up -d --no-deps app

# Подождать запуска
sleep 5

# Проверить
curl -f http://localhost:8000/health || {
    echo "Health check failed! Rolling back..."
    # Откат к предыдущему образу
    IMAGE_TAG=$PREV_TAG docker compose up -d --no-deps app
    exit 1
}
```

---

## 8.4 Rollback — откат к предыдущей версии

### Сохраняем текущий тег

На сервере, ПЕРЕД деплоем:

```bash
# Сохранить текущий тег
cat /opt/myapp/.env.deploy | grep IMAGE_TAG | cut -d= -f2 > /opt/myapp/.prev_tag
```

### Скрипт rollback

Создай `/opt/myapp/rollback.sh`:

```bash
#!/bin/bash
set -e

cd /opt/myapp

# Прочитать предыдущий тег
if [ ! -f .prev_tag ]; then
    echo "❌ No previous tag found"
    exit 1
fi

PREV_TAG=$(cat .prev_tag)
echo "🔄 Rolling back to $PREV_TAG"

# Обновить .env.deploy
echo "IMAGE_TAG=$PREV_TAG" > .env.deploy

# Пересоздать контейнер
export IMAGE_TAG=$PREV_TAG
docker compose pull app
docker compose up -d --no-deps app

# Проверить
sleep 5
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Rollback successful"
else
    echo "❌ Rollback failed! Previous version also broken!"
    exit 1
fi
```

```bash
chmod +x /opt/myapp/rollback.sh
```

### Использовать

```bash
ssh deploy@server
./rollback.sh
🔄 Rolling back to abc123def456
✅ Rollback successful
```

---

## 8.5 Полный деплой с rollback

```yaml
deploy:
  needs: build-and-push
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to server
      uses: appleboy/ssh-action@v1
      with:
        host: ${{ secrets.SERVER_HOST }}
        username: deploy
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /opt/myapp

          # Сохранить текущий тег
          if [ -f .env.deploy ]; then
            grep IMAGE_TAG .env.deploy | cut -d= -f2 > .prev_tag
          fi

          # Деплой
          echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
          export IMAGE_TAG=${{ github.sha }}
          docker compose pull app
          docker compose up -d --no-deps app
          docker image prune -f

          # Проверка
          sleep 5
          if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "❌ Health check failed! Rolling back..."

            # Откат
            if [ -f .prev_tag ]; then
              PREV_TAG=$(cat .prev_tag)
              echo "IMAGE_TAG=$PREV_TAG" > .env.deploy
              export IMAGE_TAG=$PREV_TAG
              docker compose pull app
              docker compose up -d --no-deps app
              echo "🔄 Rolled back to $PREV_TAG"
            fi

            exit 1
          fi

          echo "✅ Deploy successful"
```

### Что происходит при провале

```
Push → CI → деплой
              │
              │ health check failed
              │
              ├── автоматически rollback
              │
              ▼
         предыдущая версия работает
```

CI покажет ❌ но сайт продолжает работать на старой версии.

> **Запомни:** Rollback = страховка.
> Лучше иметь и не использовать, чем necesitar и не иметь.

---

## 8.6 Blue-green деплой (концепция)

```
Интернет
    │
    ▼
[ Nginx ] ──→ Blue (v1.0)   ← сейчас работает
          ──→ Green (v2.0)  ← новый, тестируем
```

1. Развернуть v2.0 рядом с v1.0
2. Проверить что v2.0 работает
3. Переключить Nginx на v2.0
4. Если проблема — переключить обратно на v1.0

```
Интернет
    │
    ▼
[ Nginx ] ──→ Blue (v1.0)   ← standby
          ──→ Green (v2.0)  ← теперь работает
```

> **Запомни:** Blue-green — для серьёзных продакшн проектов.
> Для обучения достаточно rolling update + rollback.

---

## 8.7 Ручное подтверждение перед продакшном

Не всегда хочется автодеплой в production.

### Environment с approval

GitHub → Settings → Environments → production:

```
✅ Required reviewers
  ← выбери кто подтверждает
```

### Workflow

```yaml
deploy-production:
  needs: build-and-push
  runs-on: ubuntu-latest
  environment: production     ← требует подтверждения
  steps:
    - name: Deploy
      uses: appleboy/ssh-action@v1
      with:
        host: ${{ secrets.SERVER_HOST }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /opt/myapp
          docker compose pull app
          docker compose up -d --no-deps app
```

### В интерфейсе GitHub

```
Deploy production
  ⏳ Waiting for approval

  Requested: adelfos
  [Approve and deploy] [Reject]
```

После approval — job запускается.

---

## 📝 Упражнения

### Упражнение 8.1: Rolling update
**Задача:**
1. Замени в скрипте деплоя `docker compose up -d` на `docker compose up -d --no-deps app`
2. Запушь — даунтайм меньше?

### Упражнение 8.2: Rollback-скрипт
**Задача:**
1. Создай `rollback.sh` на сервере (как в 8.4)
2. Сделай выполняемым: `chmod +x rollback.sh`
3. Соверши деплой
4. Запусти `./rollback.sh` — откатился?
5. Проверь: `cat .env.deploy` — тег изменился?

### Упражнение 8.3: Автоматический rollback в CI
**Задача:**
1. Добавь rollback-логику в ssh-action (как в 8.5)
2. Сделай коммит который сломает health endpoint
3. Запушь — CI показал ❌ но rollback вернул рабочую версию?

### Упражнение 8.4: Ручное подтверждение
**Задача:**
1. Создай Environment `production` с Required reviewers
2. Создай workflow с `environment: production`
3. Запушь — job ждёт подтверждения?
4. Нажми Approve — деплой прошёл?

### Упражнение 8.5: DevOps Think
**Задача:** «Rollback тоже не работает. Новая версия сломана и предыдущая тоже. Что делать?»

Подсказки:
1. Почему предыдущая версия сломана? (может она не менялась)
2. Проблема в данных (БД), не в коде?
3. Может миграция БД сломала? (нужен rollback миграции)
4. Когда последний раз делал бэкап БД?

---

## 📋 Чеклист главы 8

- [ ] Я понимаю проблему даунтайма при простом деплое
- [ ] Я могу использовать rolling update (`up -d --no-deps`)
- [ ] Я понимаю зачем healthcheck после деплоя
- [ ] Я могу написать rollback-скрипт
- [ ] Я могу добавить автоматический rollback в CI
- [ ] Я понимаю концепцию blue-green деплоя
- [ ] Я могу настроить ручное подтверждение (Environment approval)
- [ ] Я понимаю что rollback — страховка, не панацея

**Всё отметил?** Переходи к Главе 9 — итоговый проект.
