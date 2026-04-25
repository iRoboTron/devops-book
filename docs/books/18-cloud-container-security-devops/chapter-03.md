# Глава 3: Secrets и конфиденциальные данные

> **Запомни:** облако и контейнеры ускоряют доставку, но также ускоряют утечку секретов через env, image layers, CI logs и object storage.

---

## 3.1 Контекст и границы

Секреты живут дольше, чем хотелось бы: в истории команд, в image layers, в debug output, в backup snapshot и в слишком широких IAM ролях.

Нужно отличать конфигурацию, которую можно спокойно версионировать, от секретов, которые требуют отдельного жизненного цикла, ротации и контроля доступа.

Эта глава особенно полезна для приложений в контейнерах, CI/CD и облачных сервисов с токенами, DSN и ключами.

---

## 3.2 Как выглядит риск

Типовые слабые места:
- секреты baked-in в Docker image — токен попадает в слой образа и уезжает в registry вместе с приложением.
  Проверить: `docker history`, `docker inspect` и поиск строк через `docker save | strings`.
- CI выводит переменные окружения в лог — любой, кто видит job log, видит и секрет.
  Проверить: поиск `printenv`, `env`, `echo $...`, `set -x` в pipeline.
- bucket или backup содержит `.env` и дампы БД — резервная копия превращается в концентрат секретов.
  Проверить: список объектов, backup retention и контроль доступа к ним.
- секреты лежат в compose или k8s manifest как plain text — инфраструктурный репозиторий становится точкой утечки.
  Проверить: `rg -n "SECRET|TOKEN|PASSWORD|DATABASE_URL"`.
- нет ротации и инвентаризации владельцев секретов — после утечки никто не знает, что именно и кто должен менять.
  Проверить: есть ли owner, дата ротации и runbook замены.

### Где особенно важно
- Docker
- GitHub Actions
- cloud secret manager
- object storage
- managed DB

---

## 3.3 Что строит защитник

- secrets outside images and repo;
- masking и отсутствие echo чувствительных переменных в CI;
- secret manager или хотя бы защищенное хранение на хосте;
- ротация ключей и owner для каждого секрета;
- поиск утечек по репозиторию и runtime.

### Практический результат главы
- ты умеешь объяснить, откуда секрет попадает в контейнер и куда может утечь;
- можешь отличить config value от секрета;
- понимаешь, какие слои Docker и CI опасны для утечки.

```dockerfile
# Никогда не делай так
ENV DATABASE_URL=postgres://user:pass@db/app
```

```bash
# Лучше передавать секрет только в runtime
docker run --env-file .env myapp:prod
```

## 3.3а Как секрет попадает в layer

Плохой Dockerfile:

```dockerfile
FROM python:3.12-slim
ENV DATABASE_URL=postgres://user:SuperSecret@db:5432/app
RUN pip install -r requirements.txt
COPY . .
```

Собери и посмотри историю слоёв:

```bash
docker build -t myapp:bad .
docker history myapp:bad
```

Пример результата:

```
IMAGE     CREATED   CREATED BY                                      SIZE
abc123    5m ago    COPY . .                                        2.1MB
def456    5m ago    RUN pip install -r requirements.txt             45MB
ghi789    5m ago    ENV DATABASE_URL=postgres://user:SuperSecret... 0B
```

Даже если слой весит `0B`, секрет остаётся в метаданных образа.

Как найти утечку:

```bash
docker inspect myapp:bad | grep -i "DATABASE_URL\\|SECRET\\|PASSWORD"
docker save myapp:bad | tar -xO | strings | grep -i "password\\|secret\\|token" | head -20
```

Правильный подход:

```dockerfile
FROM python:3.12-slim
RUN pip install -r requirements.txt
COPY . .
```

```bash
docker run --env-file .env myapp:prod
```

---

## 3.4 Практика

### Шаг 1: Проверь образ и build context
- убедись, что секреты не копируются в image layers;
- проверь .dockerignore и build args.

```bash
rg -n "SECRET|TOKEN|PASSWORD|DATABASE_URL" Dockerfile* docker-compose*.yml .github/ .env* || true
trivy image --scanners secret myapp:latest
```

Пример секрета, найденного сканером:

```
myapp:latest (debian 12.5)
Total: 2 (SECRET: 2)

Target         Secret Type      Match
/app/.env      Generic API Key  API_KEY=sk-proj-abc123...
/app/config    AWS Access Key   AKIA...
```

### Шаг 2: Проверь runtime env
- на своем стенде посмотри, какие env действительно получает контейнер;
- зафиксируй, что там только нужный минимум.

```bash
docker inspect CONTAINER_NAME | rg -n 'Env|SECRET|TOKEN|PASSWORD'
```

### Шаг 3: Проверь CI logs и storage
- найди места, где pipeline может печатать env или артефакты с секретами;
- отдельно оцени backup и object storage.

```bash
rg -n "printenv|env|echo \$|set -x" .github/ || true
```

### Что нужно явно показать
- где хранятся секреты проекта;
- как они попадают в runtime;
- нет ли секретов в образе и CI логах;
- как устроена ротация ключей.

---

## 3.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- на своем стенде запусти поиск типовых секретов по repo и compose-файлам;
- проверь, что секреты не попадают в docker history и не baked-in в image;
- сделай controlled rotation одного тестового секрета и проверь, что сервис перезапускается штатно.

---

## 3.6 Типовые ошибки

- передавать секрет через ENV в Dockerfile;
- печать env в CI ради отладки;
- путать .env.example и реальные значения;
- не знать владельца и срок жизни секрета.

---

## 3.7 Чеклист главы

- [ ] Секреты у меня не baked-in в image и repo
- [ ] Я проверил runtime env контейнеров
- [ ] CI не печатает чувствительные значения
- [ ] Для секретов есть инвентаризация и ротация
