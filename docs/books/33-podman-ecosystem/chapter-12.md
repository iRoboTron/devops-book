# Глава 12: Podman в CI/CD — практические сценарии

## Что вы узнаете

- как собирать и пушить образы в GitLab CI и GitHub Actions без `--privileged`;
- почему Docker socket в CI — это дыра безопасности и как её закрыть;
- как кэшировать слои образов между сборками;
- как тестировать через Testcontainers с Podman.

---

## Почему Docker в CI — проблема безопасности

Стандартная схема CI с Docker выглядит так:

```yaml
# GitLab CI — плохой пример
build:
  image: docker:latest
  services:
    - docker:dind          # Docker-in-Docker
  variables:
    DOCKER_HOST: tcp://docker:2375
  script:
    - docker build -t myapp .
    - docker push myapp
```

Что здесь плохо:

1. **Docker-in-Docker требует `--privileged`** — CI-контейнер получает полный доступ к хосту.
2. **Альтернатива: монтировать `/var/run/docker.sock`** — CI-контейнер получает root-доступ через socket.
3. **Любой код в CI** (в том числе вредоносный pull request) может выполниться с правами root на CI-сервере.

С Podman ни то ни другое не нужно — rootless сборка работает без привилегий.

---

## GitLab CI: сборка через Podman

### Базовый pipeline

```yaml
# .gitlab-ci.yml
variables:
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  IMAGE_LATEST: $CI_REGISTRY_IMAGE:latest

stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: quay.io/podman/stable   # официальный образ с Podman
  before_script:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - podman build -t $IMAGE_TAG .
    - podman push $IMAGE_TAG
    # Тегировать как latest при пуше в main
    - |
      if [ "$CI_COMMIT_BRANCH" = "main" ]; then
        podman tag $IMAGE_TAG $IMAGE_LATEST
        podman push $IMAGE_LATEST
      fi
  # Не нужно: privileged: true
  # Не нужно: services: docker:dind
```

### С кэшированием слоёв

```yaml
build-with-cache:
  stage: build
  image: quay.io/podman/stable
  before_script:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    # Попробовать скачать кэш-образ (ошибка если нет — это нормально)
    - podman pull $CI_REGISTRY_IMAGE:cache || true

    # Собрать с кэшем
    - podman build
        --layers
        --cache-from $CI_REGISTRY_IMAGE:cache
        -t $IMAGE_TAG
        .

    - podman push $IMAGE_TAG

    # Обновить кэш (только на main)
    - |
      if [ "$CI_COMMIT_BRANCH" = "main" ]; then
        podman tag $IMAGE_TAG $CI_REGISTRY_IMAGE:cache
        podman push $CI_REGISTRY_IMAGE:cache
      fi
```

### Multi-stage с параллельными джобами

```yaml
variables:
  IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

stages:
  - build
  - test

build:
  stage: build
  image: quay.io/podman/stable
  script:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - podman build --target builder -t $IMAGE-builder .
    - podman build -t $IMAGE .
    - podman push $IMAGE

test-unit:
  stage: test
  image: $IMAGE    # использует только что собранный образ
  needs: [build]
  script:
    - pytest tests/unit/ -v

test-integration:
  stage: test
  image: quay.io/podman/stable
  needs: [build]
  before_script:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    # Запустить зависимости (например, postgres)
    - podman run -d --name postgres
        -e POSTGRES_PASSWORD=test
        -e POSTGRES_DB=testdb
        postgres:16-alpine

    # Подождать готовности
    - |
      for i in $(seq 1 30); do
        podman exec postgres pg_isready -U postgres && break || sleep 1
      done

    # Запустить тесты
    - podman run --rm
        --network container:postgres
        -e DATABASE_URL=postgresql://postgres:test@localhost/testdb
        $IMAGE
        pytest tests/integration/ -v
  after_script:
    - podman stop postgres || true
    - podman rm postgres || true
```

---

## GitHub Actions: сборка через Podman

### Базовый workflow

```yaml
# .github/workflows/build.yml
name: Build and Push

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Podman
        run: |
          sudo apt-get update
          sudo apt-get install -y podman

      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
          podman login ${{ env.REGISTRY }} \
            -u ${{ github.actor }} \
            --password-stdin

      - name: Build image
        run: |
          podman build \
            -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest \
            .

      - name: Push image
        if: github.event_name != 'pull_request'
        run: |
          podman push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          podman push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
```

### С buildah для максимальной совместимости

```yaml
  build-with-buildah:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Install tools
        run: sudo apt-get install -y buildah skopeo

      - name: Login
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | \
          buildah login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Build
        env:
          BUILDAH_ISOLATION: chroot
        run: |
          buildah bud \
            --layers \
            -t ghcr.io/${{ github.repository }}:${{ github.sha }} \
            .

      - name: Push
        run: |
          buildah push ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## Tekton / Argo Workflows: rootless в кластере

```yaml
# Tekton Task для сборки через buildah в K8s
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: buildah-build
spec:
  params:
    - name: IMAGE
      type: string
    - name: DOCKERFILE
      default: ./Dockerfile

  steps:
    - name: build
      image: quay.io/buildah/stable
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        # Не нужно: privileged: true
      env:
        - name: BUILDAH_ISOLATION
          value: chroot
        - name: STORAGE_DRIVER
          value: vfs
      script: |
        buildah bud \
          -f $(params.DOCKERFILE) \
          -t $(params.IMAGE) \
          .
        buildah push $(params.IMAGE)
```

---

## Testcontainers с Podman

Testcontainers — библиотека для интеграционных тестов которая запускает зависимости (БД, очереди) в контейнерах. По умолчанию ждёт Docker socket.

### Настройка для Podman

```bash
# Включить Podman socket
systemctl --user enable --now podman.socket

# Указать путь к сокету
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock

# Отключить Ryuk (cleanup daemon — не работает в rootless)
export TESTCONTAINERS_RYUK_DISABLED=true
```

### Python (pytest + testcontainers)

```python
# tests/test_db.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

def test_database_connection(postgres):
    engine = create_engine(postgres.get_connection_url())
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

```bash
# Запустить тесты
DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock \
TESTCONTAINERS_RYUK_DISABLED=true \
pytest tests/ -v
```

### В GitLab CI

```yaml
integration-tests:
  stage: test
  image: quay.io/podman/stable
  variables:
    DOCKER_HOST: unix:///run/user/1000/podman/podman.sock
    TESTCONTAINERS_RYUK_DISABLED: "true"
  before_script:
    # Запустить Podman socket в фоне
    - podman system service --time=0 unix:///run/user/1000/podman/podman.sock &
    - sleep 2
    - pip install pytest testcontainers
  script:
    - pytest tests/integration/ -v
```

---

## Безопасность секретов в CI

Никогда не передавайте пароли реестров через переменные окружения напрямую. Используйте CI-встроенные механизмы:

```yaml
# GitLab CI: секреты через masked variables
# Установить в Settings → CI/CD → Variables:
# CI_REGISTRY_USER, CI_REGISTRY_PASSWORD — встроены GitLab
# CUSTOM_REGISTRY_TOKEN — добавить вручную, masked=true

build:
  script:
    # GitLab встроенные:
    - podman login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    # Кастомный реестр:
    - podman login -u myuser -p $CUSTOM_REGISTRY_TOKEN registry.example.com
```

```yaml
# GitHub Actions: secrets из Settings → Secrets
- name: Login to private registry
  run: |
    echo "${{ secrets.REGISTRY_TOKEN }}" | \
    podman login registry.example.com \
      -u ${{ secrets.REGISTRY_USER }} \
      --password-stdin
```

---

## Оптимизация времени сборки

### Многоступенчатая сборка (multi-stage)

```dockerfile
# Dockerfile с multi-stage: разделить сборку и runtime
FROM python:3.12 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
USER 1000
CMD ["python", "main.py"]
```

```bash
# Кэшировать builder отдельно
podman build --target builder -t myapp:builder .
podman build --cache-from myapp:builder -t myapp:latest .
```

### Параллельная сборка для нескольких платформ

```yaml
# GitLab CI: параллельная сборка для amd64 и arm64
build:
  parallel:
    matrix:
      - PLATFORM: linux/amd64
        SUFFIX: amd64
      - PLATFORM: linux/arm64
        SUFFIX: arm64
  image: quay.io/podman/stable
  script:
    - podman build --platform $PLATFORM -t $IMAGE_TAG-$SUFFIX .
    - podman push $IMAGE_TAG-$SUFFIX
```

---

## Типичные ошибки в CI

**`Error: creating build container: ... overlay: ...`**
В CI-контейнере не работает overlay filesystem. Добавить:
```yaml
variables:
  STORAGE_DRIVER: vfs
```

**`Error: short-name resolution enforced`**
Не настроены `unqualified-search-registries`. В образе `quay.io/podman/stable` это уже настроено. На кастомных образах — добавить конфиг:
```yaml
before_script:
  - echo 'unqualified-search-registries = ["docker.io"]' >> /etc/containers/registries.conf
```

**Testcontainers зависает ожидая Ryuk**
Установить `TESTCONTAINERS_RYUK_DISABLED=true`.

**`podman login` требует интерактивного ввода пароля**
Передавать через `--password-stdin`:
```bash
echo "$TOKEN" | podman login registry.example.com -u user --password-stdin
```

---

## Чек-лист для самопроверки

- [ ] Написал GitLab CI или GitHub Actions job который собирает образ через Podman без `privileged: true`
- [ ] Настроил кэширование слоёв через `--cache-from` и проверил что повторная сборка быстрее
- [ ] Использую секреты CI (masked variables / GitHub Secrets) для хранения токенов реестра
- [ ] Знаю как запустить Testcontainers с Podman через `DOCKER_HOST`

## Попробуйте сами

1. Создайте минимальный `.github/workflows/build.yml` который:
   - Собирает образ из `FROM alpine` Dockerfile
   - Пушит в GHCR
   - Запускается при каждом push в main
   Проверьте что workflow зелёный и образ появился в GHCR.

2. Добавьте кэширование: измерьте время первой сборки, потом добавьте `--cache-from` и измерьте время второй. Какой выигрыш?

3. Если у вас есть Python-проект с тестами — попробуйте запустить их через Testcontainers с Podman вместо Docker. Что потребовалось изменить?
