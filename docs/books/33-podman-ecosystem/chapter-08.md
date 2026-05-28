# Глава 8: Реестры образов — за пределами Docker Hub

## Что вы узнаете

- какие реестры кроме Docker Hub используются в реальной жизни и зачем;
- как аутентифицироваться в нескольких реестрах одновременно;
- как копировать образы между реестрами без скачивания на диск;
- как поднять свой приватный реестр за 5 минут.

---

## Почему Docker Hub — это не единственный вариант

Docker Hub удобен. Но у него есть реальные ограничения:

**Rate limits для анонимных запросов.** 100 pull-запросов за 6 часов для анонимных пользователей, 200 — для зарегистрированных. В CI/CD на десятки сборок в день это проблема.

**Downtime.** Docker Hub несколько раз в год имеет перебои. Если ваш деплой зависит от pull в Docker Hub — он встаёт вместе с ним.

**Приватные образы — платно.** Бесплатный план Docker Hub даёт один приватный репозиторий. Для команды нужна подписка.

**Нет гарантии сохранности.** Docker Hub в 2020 году начал удалять образы которые не пулились 6+ месяцев.

---

## Карта реестров

```text
Реестр                Адрес               Кем управляется    Для чего
──────────────────────────────────────────────────────────────────────
Docker Hub            docker.io           Docker Inc.        Публичные образы
Quay.io               quay.io             Red Hat            Открытые и приватные образы
GitHub Container      ghcr.io             GitHub             Привязан к GitHub репозиторию
Registry
Google Container      gcr.io              Google             GKE, Google Cloud
Registry
Artifact Registry     <region>-docker.    Google             Замена GCR, много форматов
                      pkg.dev
Amazon ECR            <account>.dkr.      AWS                EKS, AWS экосистема
                      ecr.<region>.
                      amazonaws.com
Azure Container       <name>.azurecr.io   Microsoft          AKS, Azure
Registry
registry.k8s.io       registry.k8s.io     CNCF/K8s           Официальные K8s образы
Harbor                self-hosted         Open source        Self-hosted enterprise
```

Официальные образы для компонентов K8s:
```bash
# Правильно (registry.k8s.io):
podman pull registry.k8s.io/pause:3.9
podman pull registry.k8s.io/coredns/coredns:v1.10.1

# Устарело (k8s.gcr.io):
# k8s.gcr.io переехал на registry.k8s.io в 2023 году
```

---

## Аутентификация в нескольких реестрах

Учётные данные хранятся в `~/.config/containers/auth.json`. Можно одновременно быть залогиненным во все реестры.

```bash
# Docker Hub
podman login docker.io
# Username: myusername
# Password: (вводить или из переменной)

# Quay.io
podman login quay.io
# Username: myusername
# Password: (Robot Account токен из веб-интерфейса Quay)

# GitHub Container Registry (GHCR)
# Нужен Personal Access Token с правом read:packages / write:packages
echo $GITHUB_TOKEN | podman login ghcr.io -u myusername --password-stdin

# Amazon ECR (токен живёт 12 часов)
aws ecr get-login-password --region us-east-1 \
  | podman login --username AWS \
    --password-stdin \
    123456789.dkr.ecr.us-east-1.amazonaws.com

# Google Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Посмотреть текущие сессии

```bash
cat ~/.config/containers/auth.json
# {
#   "auths": {
#     "docker.io": {"auth": "base64..."},
#     "quay.io": {"auth": "base64..."},
#     "ghcr.io": {"auth": "base64..."}
#   }
# }

# base64 в auth — это username:password в base64, не шифрование!
# Держите этот файл в тайне.
```

### Выйти из реестра

```bash
podman logout docker.io
podman logout ghcr.io

# Выйти из всех реестров
podman logout --all
```

---

## Работа с образами без скачивания: skopeo

`skopeo` — лучший инструмент для работы с образами на уровне реестров. Не скачивает образ на диск, не запускает контейнеры — только передаёт данные между реестрами.

### Инспектировать образ

```bash
# Посмотреть метаданные без скачивания
skopeo inspect docker://nginx:alpine

# Только нужные поля
skopeo inspect docker://nginx:alpine | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Tags:', len(d.get('RepoTags', [])), 'tags available')
print('Created:', d['Created'])
print('Architecture:', d['Architecture'])
print('Layers:', len(d['Layers']))
"

# Для приватного реестра с аутентификацией:
skopeo inspect \
  --creds myuser:mypassword \
  docker://registry.example.com/myapp:latest
```

### Копировать образ между реестрами

```bash
# Docker Hub → GHCR (без скачивания на диск)
skopeo copy \
  docker://docker.io/library/nginx:alpine \
  docker://ghcr.io/myorg/nginx:alpine

# С аутентификацией:
skopeo copy \
  --src-creds myuser:srcpassword \
  --dest-creds myuser:destpassword \
  docker://registry-a.example.com/app:v1.0 \
  docker://registry-b.example.com/app:v1.0

# Скопировать все теги образа:
skopeo copy --all \
  docker://nginx \
  docker://registry.example.com/nginx

# Скопировать в локальную директорию (OCI layout):
skopeo copy \
  docker://nginx:alpine \
  oci:/tmp/nginx-oci:alpine
```

### Синхронизация реестров (mirror)

```bash
# Создать зеркало образов для air-gap окружения:
# Шаг 1: На машине с интернетом — синхронизировать в директорию
skopeo sync \
  --src docker \
  --dest dir \
  nginx:alpine \
  /tmp/registry-mirror/

# Шаг 2: Перенести директорию на изолированный сервер
# Шаг 3: На изолированном сервере — загрузить в локальный реестр
skopeo sync \
  --src dir \
  --dest docker \
  /tmp/registry-mirror/ \
  localhost:5000/mirror/
```

### Проверить что образы идентичны

```bash
# Сравнить digest одного образа в разных реестрах
DIGEST_HUB=$(skopeo inspect docker://nginx:latest | python3 -c "import json,sys; print(json.load(sys.stdin)['Digest'])")
DIGEST_GHCR=$(skopeo inspect docker://ghcr.io/myorg/nginx:latest | python3 -c "import json,sys; print(json.load(sys.stdin)['Digest'])")

echo "Docker Hub: $DIGEST_HUB"
echo "GHCR:       $DIGEST_GHCR"

[ "$DIGEST_HUB" = "$DIGEST_GHCR" ] && echo "✅ Идентичны" || echo "❌ Различаются"
```

---

## Свой приватный реестр за 5 минут

Для разработки, тестирования или внутреннего использования — проще всего поднять `registry:2` (Docker Distribution).

```bash
# Создать том для хранения образов
podman volume create registry-data

# Запустить реестр
podman run -d \
  --name my-registry \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \
  --restart always \
  registry:2

# Проверить
curl http://localhost:5000/v2/
# {}  ← пустой ответ означает что реестр работает
```

### Настроить как insecure registry

По умолчанию Podman требует TLS. Для localhost реестра добавим исключение:

```bash
# Создать пользовательский конфиг
cat >> ~/.config/containers/registries.conf << 'EOF'

[[registry]]
location = "localhost:5000"
insecure = true
EOF

# Или системный (для всех пользователей):
sudo bash -c 'cat >> /etc/containers/registries.conf << EOF

[[registry]]
location = "localhost:5000"
insecure = true
EOF'
```

### Использовать локальный реестр

```bash
# Загрузить образ в локальный реестр
podman pull nginx:alpine
podman tag nginx:alpine localhost:5000/nginx:alpine
podman push localhost:5000/nginx:alpine

# Загрузить свой образ
podman build -t localhost:5000/myapp:v1.0 .
podman push localhost:5000/myapp:v1.0

# Запустить из локального реестра
podman run -d localhost:5000/myapp:v1.0

# Список образов в реестре:
curl -s http://localhost:5000/v2/_catalog | python3 -m json.tool
# {
#   "repositories": ["nginx", "myapp"]
# }

# Список тегов конкретного образа:
curl -s http://localhost:5000/v2/myapp/tags/list | python3 -m json.tool
# {
#   "name": "myapp",
#   "tags": ["v1.0", "v1.1", "latest"]
# }
```

### Реестр с TLS (для production)

Для использования вне localhost — нужен TLS. Самый простой вариант — самоподписанный сертификат:

```bash
# Создать сертификат
mkdir -p ~/registry-certs
openssl req -newkey rsa:4096 -nodes -sha256 \
  -keyout ~/registry-certs/domain.key \
  -x509 -days 365 \
  -out ~/registry-certs/domain.crt \
  -subj "/CN=registry.local" \
  -addext "subjectAltName=IP:192.168.1.100,DNS:registry.local"

# Запустить реестр с TLS
podman run -d \
  --name my-registry-tls \
  -p 443:443 \
  -v ~/registry-certs:/certs:ro \
  -v registry-data:/var/lib/registry \
  -e REGISTRY_HTTP_ADDR=0.0.0.0:443 \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
  registry:2
```

---

## Harbor — enterprise реестр (обзорно)

**Harbor** — полноценный корпоративный реестр с открытым кодом от VMware. Если Registry:2 — это «хранилище образов», то Harbor — это «платформа управления образами».

Что добавляет Harbor поверх Registry:
- **Веб-интерфейс** с управлением пользователями и ролями (RBAC)
- **Сканирование уязвимостей** (Trivy, Clair): показывает CVE в образах
- **Репликация**: автосинхронизация с другими реестрами
- **Подпись образов** (Notary): верификация что образ не подменён
- **Quota**: ограничения на место для проектов
- **Helm chart репозиторий**: хранение chart-ов рядом с образами

Harbor стоит рассмотреть когда:
- Команда больше 5 человек и нужны роли
- Требования compliance: сканирование образов, логирование доступа
- Air-gap деплой: нужна репликация с Docker Hub внутрь сети

Установка Harbor (не в этой книге — отдельная тема), но важно знать что он существует.

---

## Rate limits Docker Hub и как их избежать

```bash
# Проверить текущий лимит (анонимный запрос)
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
curl -s -I -H "Authorization: Bearer $TOKEN" \
  https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest \
  | grep -i ratelimit
# RateLimit-Limit: 100;w=21600
# RateLimit-Remaining: 97;w=21600
```

Стратегии работы с лимитами:
1. **Залогиниться:** `podman login docker.io` — бесплатный аккаунт даёт 200 запросов.
2. **Использовать mirror:** настроить локальный реестр или Quay.io как зеркало.
3. **Pull by digest:** если образ уже скачан — повторный pull не расходует лимит.
4. **Кэшировать в CI:** скачать образ один раз, сохранить в своём реестре.

```yaml
# Пример: в GitLab CI скачать через свой прокси-реестр
variables:
  NGINX_IMAGE: registry.example.com/mirror/nginx:alpine
  # Вместо: docker.io/library/nginx:alpine
```

---

## Типичные ошибки

**`unauthorized: authentication required`**
Не выполнен `podman login` для этого реестра. Или токен истёк (ECR — 12 часов, GHCR — зависит от настроек).

**`x509: certificate signed by unknown authority`**
Используете реестр с самоподписанным сертификатом. Решение: добавить `insecure = true` в `registries.conf`, или добавить сертификат в доверенные:
```bash
sudo cp registry.crt /etc/containers/certs.d/registry.local/ca.crt
```

**Rate limit от Docker Hub в CI**
Добавить `podman login docker.io` в начало пайплайна с учётными данными из secrets, или переключиться на Quay.io для базовых образов.

**`skopeo copy` падает с TLS ошибкой**
Для insecure реестра:
```bash
skopeo copy --dest-tls-verify=false \
  docker://nginx:alpine \
  docker://localhost:5000/nginx:alpine
```

---

## Чек-лист для самопроверки

- [ ] Вошёл минимум в два реестра (docker.io и ghcr.io или quay.io)
- [ ] Выполнил `skopeo inspect` для образа и нашёл его digest
- [ ] Скопировал образ между реестрами через `skopeo copy`
- [ ] Поднял локальный реестр через `podman run registry:2` и запушил в него образ
- [ ] Знаю где хранятся учётные данные реестров (`~/.config/containers/auth.json`)

## Попробуйте сами

1. Сравните размер `nginx:latest` и `nginx:alpine` без скачивания:
   ```bash
   skopeo inspect docker://nginx:latest | python3 -c "import json,sys; d=json.load(sys.stdin); print('layers:', len(d['Layers']))"
   skopeo inspect docker://nginx:alpine | python3 -c "import json,sys; d=json.load(sys.stdin); print('layers:', len(d['Layers']))"
   ```

2. Поднимите локальный реестр, запушите образ, остановите реестр, снова запустите и проверьте что образ сохранился:
   ```bash
   podman volume create registry-data
   podman run -d --name reg -p 5000:5000 -v registry-data:/var/lib/registry registry:2
   podman tag alpine:latest localhost:5000/myalpine:test
   podman push localhost:5000/myalpine:test
   podman stop reg && podman rm reg
   podman run -d --name reg -p 5000:5000 -v registry-data:/var/lib/registry registry:2
   curl http://localhost:5000/v2/_catalog
   # Образ должен быть там
   ```

3. Проверьте что в `~/.config/containers/auth.json` хранятся ваши учётные данные. Декодируйте base64 из поля `auth` и убедитесь что это `username:password`:
   ```bash
   cat ~/.config/containers/auth.json | python3 -c "
   import json, base64, sys
   d = json.load(sys.stdin)
   for reg, creds in d['auths'].items():
       decoded = base64.b64decode(creds['auth']).decode()
       print(f'{reg}: {decoded[:20]}...')  # Показать только начало
   "
   ```
