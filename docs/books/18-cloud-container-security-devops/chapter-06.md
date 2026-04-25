# Глава 6: Registry и supply chain

> **Запомни:** после сборки безопасность не заканчивается: образ нужно правильно хранить, сканировать и продвигать по средам.

---

## 6.1 Контекст и границы

Registry — это не просто склад контейнеров. Это точка доверия: какие образы туда попадают, кто имеет право пушить, как выбирается версия для production и как откатываться.

Supply chain риск здесь связан с неподписанными артефактами, latest, широкими правами на push и отсутствием правила “что именно считается продовым образом”.

Эта глава особенно полезна для команд с registry, CI/CD и несколькими окружениями доставки.

---

## 6.2 Как выглядит риск

Типовые слабые места:
- образы пушатся под тегом `latest` и им же выкатываются — один и тот же тег означает разные биты в разное время.
  Проверить: `rg -n "latest|image:" docker-compose*.yml .github/ .gitlab-ci.yml`.
- один и тот же registry credential есть у всех — утёкший токен позволяет и читать, и пушить, и ломать supply chain.
  Проверить: список пользователей и ролей в registry.
- нет сканирования образа перед публикацией — уязвимый образ попадает в prod без единого сигнала.
  Проверить: pipeline и наличие `trivy`/другого сканера.
- production тянет образ напрямую из ветки разработки — release boundary отсутствует.
  Проверить: какой pipeline и из какой ветки публикует production-артефакт.
- нет immutable tags или digests в deploy — откат и аудит зависят от того, не перезаписал ли кто-то тег.
  Проверить: `docker inspect` и deploy manifests.

### Где особенно важно
- private registry
- GitHub/GitLab registry
- self-hosted Harbor
- Docker Hub

---

## 6.3 Что строит защитник

- разделение прав read, push и admin;
- immutable tags и deploy по digest;
- сканирование образа до и после публикации;
- отдельные репозитории для prod и non-prod;
- audit trail публикаций.

### Практический результат главы
- ты понимаешь, какой образ попадает в production и почему именно он;
- умеешь строить политику тегов и digests;
- можешь объяснить, как проверить provenance публикации.

```bash
docker pull registry.example.com/myapp@sha256:...
trivy image registry.example.com/myapp:1.4.3
```

---

## 6.4 Практика

### Шаг 1: Разбери текущую стратегию тегов
- проверь, используются ли immutable версии или все живет на latest;
- раздели build tag и release tag.

```bash
rg -n "latest|image:" docker-compose*.yml .github/ .gitlab-ci.yml || true
```

### Шаг 2: Ограничь доступ к registry
- проверь, у кого есть push и admin права;
- для CI оставь только те разрешения, которые нужны для конкретного репозитория.

```bash
cat ~/.docker/config.json 2>/dev/null || true
rg -n "docker login|ghcr.io|CI_REGISTRY|REGISTRY_" .github/ .gitlab-ci.yml .gitlab-ci.yml 2>/dev/null || true
```

### Шаг 3: Проверь артефакты на публикации
- перед релизом сканируй образ и фиксируй digest;
- проверь, что прод тянет именно утвержденный digest.

```bash
trivy image --severity HIGH,CRITICAL myapp:latest
docker inspect myapp:release | rg -n 'RepoDigests'
```

Пример результата сканирования:

```
myapp:latest (debian 12.5)
Total: 3 (HIGH: 2, CRITICAL: 1)

Library    Vulnerability  Severity  Installed Version  Fixed Version
openssl    CVE-2023-5678  CRITICAL  3.0.2-0ubuntu1     3.0.2-0ubuntu1.12
libssl3    CVE-2024-0727  HIGH      3.0.2-0ubuntu1     3.0.2-0ubuntu1.14
python3.11 CVE-2023-6597  HIGH      3.11.2             3.11.8
```

Как действовать:
- `CRITICAL` в base image обычно означает обновить `FROM` и пересобрать образ;
- `HIGH` в приложенческой зависимости означает обновить пакет и прогнать тесты;
- не надо обновлять всё разом без понимания, что именно изменится.

Проверка digest вместо `latest`:

```bash
docker pull myapp:latest
docker pull myapp@sha256:abc123def456...
docker inspect --format='{{index .RepoDigests 0}}' myapp:latest
```

В deploy-манифестах production лучше держать строку вида:

```yaml
image: ghcr.io/user/myapp@sha256:abc123def456...
```

### Что нужно явно показать
- как тегируется релизный образ;
- кто имеет право публиковать в registry;
- какой digest у production-образа;
- какой сканер используется перед выкладкой.

---

## 6.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- переведи свой тестовый deploy с тега на digest и проверь, что rollout предсказуем;
- сравни скан-результат до и после обновления base image;
- зафиксируй, что latest не используется как production контракт.

---

## 6.6 Типовые ошибки

- деплой по latest;
- не разделять права push и read;
- не хранить digest релиза;
- не иметь журнала публикации образа.

---

## 6.7 Чеклист главы

- [ ] У меня есть внятная стратегия тегов и digests
- [ ] Registry-права разделены по ролям
- [ ] Образы сканируются до публикации и перед релизом
- [ ] Production выкатывает утвержденный артефакт, а не плавающий тег
