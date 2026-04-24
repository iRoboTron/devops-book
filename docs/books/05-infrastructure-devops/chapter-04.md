# Глава 4: Миграции базы данных

> **Запомни:** Изменил модель в коде но не обновил схему БД → 500 ошибка. Миграции — это версионированные изменения схемы, которые применяются автоматически.

---

## 4.1 Проблема: код и схема БД рассинхронизированы

### Сценарий

```
1. Ты добавил поле "email" в модель User
2. Запушил код
3. CI/CD деплоит новую версию
4. Приложение пытается читать "email" → колонки нет в БД
5. 500 ошибка для всех пользователей
```

**Без миграций:** ты вручную заходишь в БД и делаешь `ALTER TABLE`.
**С миграциями:** миграция применяется автоматически до запуска приложения.

---

## 4.2 Что такое миграция

**Миграция** — файл с изменениями схемы БД.

```
migrations/
├── 001_create_users.py
├── 002_add_email_to_users.py
├── 003_create_posts.py
└── 004_add_index_on_posts_created.py
```

Каждая миграция имеет:
- **upgrade** — применить изменение
- **downgrade** — откатить изменение

```
upgrade:  CREATE TABLE users (...)
downgrade: DROP TABLE users
```

---

## 4.3 Alembic — миграции для SQLAlchemy/Alembic

> **Почему Alembic:** самый популярный инструмент миграций для Python.
> Используется с SQLAlchemy, FastAPI, Flask.

### Установка

```bash
pip install alembic
```

### Инициализация

```bash
cd /opt/myapp
alembic init alembic
```

Результат:

```
myapp/
├── alembic/
│   ├── env.py          ← настройка окружения
│   └── versions/       ← файлы миграций
├── alembic.ini         ← конфиг
└── main.py
```

### Настройка `alembic.ini`

```ini
sqlalchemy.url = postgresql://myapp:x7k9mP2qR5wN@db:5432/myapp_prod
```

Или через переменную окружения (лучше):

```python
# alembic/env.py
from myapp.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

---

## 4.4 Базовый workflow

### Создать миграцию

```bash
alembic revision --autogenerate -m "add users table"
```

Alembic сравнивает модели SQLAlchemy с реальной БД и создаёт миграцию:

```python
# alembic/versions/abc123_add_users_table.py
def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100)),
        sa.Column('email', sa.String(200)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

def downgrade():
    op.drop_table('users')
```

### Применить миграцию

```bash
alembic upgrade head
```

`head` = последняя миграция.

### Откатить одну миграцию

```bash
alembic downgrade -1
```

### Посмотреть историю

```bash
alembic history
abc123 -> def456, add posts table
000000 -> abc123, add users table
```

### Посмотреть статус

```bash
alembic current
Current revision: abc123 (add users table)

alembic heads
def456 (add posts table)
```

Миграция `def456` ещё не применена.

---

## 4.5 Миграции в CI/CD

> **Порядок важен:** Сначала миграция, потом деплой кода.
> Наоборот — приложение упадёт с 500 ошибкой пока миграция не применится.

### В deploy workflow

```yaml
deploy:
  needs: build-and-push
  steps:
    - name: Deploy to server
      uses: appleboy/ssh-action@v1
      with:
        host: ${{ secrets.SERVER_HOST }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /opt/myapp

          # 1. Сначала миграции БД
          docker compose run --rm app alembic upgrade head

          # 2. Потом деплой приложения
          echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
          export IMAGE_TAG=${{ github.sha }}
          docker compose pull app
          docker compose up -d --no-deps app

          # 3. Проверка
          sleep 5
          curl -f http://localhost:8000/health || exit 1
```

`docker compose run --rm app` — запускает контейнер, выполняет команду, удаляет.

---

## 4.6 Опасные миграции

### Удаление колонки

```python
# ОПАСНО: сразу удалить
def upgrade():
    op.drop_column('users', 'old_field')
```

Если код ещё использует `old_field` → 500 ошибка.

**Безопасный способ:**

```
Шаг 1: Убрать использование в коде → деплой
Шаг 2: Удалить колонку в БД → миграция
```

### Переименование колонки

```python
# ОПАСНО: RENAME (может не поддерживаться)
def upgrade():
    op.alter_column('users', 'name', new_column_name='full_name')
```

**Безопасный способ:**

```
Шаг 1: Добавить новую колонку
Шаг 2: Скопировать данные из старой в новую
Шаг 3: Обновить код чтобы использовать новую
Шаг 4: Удалить старую колонку
```

### Добавление NOT NULL без дефолта

```python
# ОПАСНО: если в таблице уже есть строки
def upgrade():
    op.alter_column('users', 'email', nullable=False)
```

**Ошибка:** `column "email" contains null values`

**Безопасный способ:**

```python
def upgrade():
    # 1. Добавить с дефолтом
    op.alter_column('users', 'email', nullable=False,
                     server_default='placeholder@example.com')
    # 2. Убрать дефолт
    op.alter_column('users', 'email', server_default=None)
```

---

## 📝 Упражнения

### Упражнение 4.1: Первая миграция
**Задача:**
1. Установи alembic: `pip install alembic psycopg2-binary`
2. Инициализируй: `alembic init alembic`
3. Настрой DATABASE_URL в `alembic.ini`
4. Создай миграцию: `alembic revision --autogenerate -m "initial"`
5. Посмотри созданный файл — что внутри?

### Упражнение 4.2: Применить и откатить
**Задача:**
1. Примени: `alembic upgrade head`
2. Проверь: `alembic current`
3. Откати: `alembic downgrade -1`
4. Проверь: `alembic current` — пусто?
5. Примени снова: `alembic upgrade head`

### Упражнение 4.3: Ручная миграция
**Задача:**
1. Создай миграцию вручную:
   ```bash
   alembic revision -m "add status to users"
   ```
2. Отредактируй файл:
   ```python
   def upgrade():
       op.add_column('users',
           sa.Column('status', sa.String(20), server_default='active'))

   def downgrade():
       op.drop_column('users', 'status')
   ```
3. Примени: `alembic upgrade head`
4. Проверь в БД: `\d users` — колонка status есть?

### Упражнение 4.4: DevOps Think
**Задача:** «Миграция упала посередине. База в непонятном состоянии. Что делать?»

Подсказки:
1. Alembic использует транзакции — если ошибка, всё откатится
2. Проверь статус: `alembic current`
3. Если миграция частично применилась — откати: `alembic downgrade -1`
4. Почини миграцию → примени снова
5. На будущее: тестируй миграции на staging перед продакшном

---

## 📋 Чеклист главы 4

- [ ] Я понимаю что такое миграции и зачем они
- [ ] Я могу инициализировать Alembic
- [ ] Я могу создать миграцию (autogenerate и вручную)
- [ ] Я могу применить (`upgrade head`) и откатить (`downgrade -1`)
- [ ] Я понимаю порядок: миграция → деплой кода (не наоборот)
- [ ] Я знаю опасные миграции и как делать их безопасно
- [ ] Миграции запускаются в CI/CD до деплоя приложения

**Всё отметил?** Переходи к Главе 5 — стратегия бэкапов.
