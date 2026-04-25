# Глава 1: CI пайплайн

---

## 1.1 GitHub Actions (альтернатива GitLab)

```yaml
name: CI
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements.txt
    - run: pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - uses: docker/build-push-action@v5
      with:
        push: true
        tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 1.2 GitLab CI (альтернатива)

```yaml
stages:
  - test
  - build

test:
  stage: test
  image: python:3.12-slim
  script:
    - pip install -r requirements.txt
    - pytest

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

Пример успешного pipeline:

```
✅ test        2m 14s
✅ build       1m 42s
  → pushed: ghcr.io/user/myapp:abc123def
```

---

## 📝 Упражнения

### Упражнение 1.1: Первый CI
1. Создай `.github/workflows/ci.yml` или `.gitlab-ci.yml`
2. Добавь jobs `test` и `build`
3. Сделай `git push`
4. Проверь pipeline в UI
5. Убедись что образ появился в registry

### Упражнение 1.2: Сломать и починить
1. Добавь намеренно падающий тест
2. Сделай `git push`
3. Убедись что pipeline упал
4. Исправь тест
5. Проверь что pipeline снова зелёный

---

## 📋 Чеклист

- [ ] CI пайплайн настроен (test → build → push)
- [ ] Образ в registry после push в main

**Переходи к Главе 2 — GitOps идея.**
