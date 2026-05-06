# Глава 9: Пользователи

> **Цель:** управлять пользователями осознанно и не терять данные.

---

## 9.1 Основные команды

```bash
occ user:list
```

# Пример вывода:
```
  - admin:
    - uid: admin
    - displayName: Administrator
  - alice:
    - uid: alice
    - displayName: Alice Smith
  - bob:
    - uid: bob
    - displayName: Bob Johnson
```

```bash
occ user:info alice
```

# Пример вывода:
```
  - uid: alice
  - displayName: Alice Smith
  - email: alice@example.com
  - cloudId: alice@nextcloud.yourdomain.com
  - enabled: true
  - quota: 10 GB
  - used: 4.23 GB (42%)
  - home: /mnt/ncdata/alice
  - lastLogin: 2024-04-27T18:45:00+00:00
  - backend: Database
  - groups: []
```

```bash
export OC_PASS="temporarypassword123"
occ user:add --password-from-env --display-name="Carol Williams" carol
```

# Пример вывода:
```
The user "carol" was created successfully
```

```bash
occ user:disable username
occ user:enable username
occ user:delete username
```

# Пример вывода user:disable:
```
The specified user is disabled
```

Удаление пользователя может затронуть файлы и shares. Перед удалением проверь данные.

---

## 9.2 Группы

```bash
occ group:list
```

# Пример вывода:
```
  - admin:
    - admin
  - team-docs:
    - alice
    - bob
```

```bash
occ group:add team
occ group:adduser team username
```

Группы нужны, чтобы не выдавать доступ каждому вручную.

---

## 9.3 Квоты

```bash
occ user:setting username files quota 10GB
```

# Пример вывода:
```
# (нет вывода при успехе — команда вернёт 0)
```

Проверить что установилось:

```bash
occ user:info alice | grep quota
```

# Пример вывода:
```
  - quota: 10 GB
  - used: 4.23 GB (42%)
```

Квоты помогают не узнать о заполненном диске слишком поздно.

---

## 9.4 Практика

Создай тестового пользователя, задай квоту, добавь в тестовую группу, потом отключи. Не тренируйся на реальном важном пользователе.

---

> **Если что-то пошло не так:**
>
> **Симптом:** пользователь забыл пароль и не может войти.
>
> ```bash
> # Сбросить пароль (пользователю придёт уведомление, если настроен email)
> occ user:resetpassword alice
>
> # Команда спросит новый пароль интерактивно.
> # Или задать через переменную окружения:
> export OC_PASS="newtemporarypassword"
> occ user:resetpassword --password-from-env alice
> ```
>
> **Симптом:** пользователь видит «Quota exceeded» и не может загружать файлы.
>
> ```bash
> # Посмотреть текущую квоту и использование
> occ user:info alice | grep -E "quota|used"
>
> # Увеличить квоту
> occ user:setting alice files quota 10GB
>
> # Или снять ограничение (использовать квоту по умолчанию)
> occ user:setting alice files quota default
>
> # Сбросить кэш квот (если вывод не обновился)
> occ files:scan --user alice
> ```
>
> **Симптом:** `occ user:delete alice` — но файлы пользователя всё ещё занимают место.
>
> При удалении пользователя файлы по умолчанию удаляются. Если этого не произошло — проверь:
> ```bash
> ls -la /var/lib/docker/volumes/nextcloud_aio_nextcloud_data/_data/ | grep alice
>
> # Если папка осталась — Nextcloud не смог удалить (например, из-за прав или ошибки)
> # Смотреть логи:
> docker logs nextcloud-aio-nextcloud --tail=50 2>&1 | grep -i "alice\|delete\|error"
> ```
>
> **Симптом:** `occ user:add` выдаёт «An account with this username already exists».
>
> ```bash
> # Проверить, возможно пользователь был отключён (disabled), а не удалён
> occ user:info alice
>
> # Если нужно — включить снова
> occ user:enable alice
> ```
