# Глава 4: Docker image hardening

> **Запомни:** безопасный контейнер начинается не с runtime-флагов, а с того, какой образ ты собираешь и что в нем реально находится.

---

## 4.1 Контекст и границы

Образ — это программный артефакт, который попадает в production. Если в нем лишние пакеты, root-пользователь, build tools и секреты, ты переносишь в runtime больше риска, чем нужно.

Хороший Dockerfile уменьшает поверхность атаки, делает состав образа предсказуемым и облегчает сканирование и обновление.

Эта глава особенно полезна для всех, кто пишет Dockerfile и публикует образы в registry.

---

## 4.2 Как выглядит риск

Типовые слабые места:
- FROM ...:latest;
- образ собирается и запускается от root;
- в runtime-образ попадают компиляторы, package managers и тестовые файлы;
- нет .dockerignore;
- обновления базового образа не контролируются.

### Где особенно важно
- backend сервисы
- worker containers
- internal tools
- CI images

---

## 4.3 Что строит защитник

- pinned base image и multi-stage build;
- не-root runtime user;
- минимальный runtime образ;
- явный .dockerignore;
- сканирование образа и регулярное обновление base image.

### Практический результат главы
- ты умеешь смотреть на Dockerfile как на security artifact;
- можешь уменьшить размер и поверхность образа;
- понимаешь, почему multi-stage build полезен и для безопасности, и для эксплуатации.

```text
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local /usr/local
COPY . .
RUN useradd -r -u 10001 app && chown -R app:app /app
USER app
CMD ["python", "main.py"]
```

---

## 4.4 Практика

### Шаг 1: Разбери текущий Dockerfile
- проверь base image, multi-stage, USER, наличие package managers и лишних файлов;
- убедись, что нет latest и секретов в build context.

```bash
sed -n '1,220p' Dockerfile
cat .dockerignore 2>/dev/null || true
```

### Шаг 2: Собери hardened image
- вынеси build dependencies в отдельный stage;
- создай отдельного runtime пользователя;
- сократи содержимое финального слоя.

```bash
docker build -t myapp:hardened .
```

### Шаг 3: Проверь состав образа
- посмотри историю слоев и список пакетов;
- сравни до и после hardening.

```bash
docker history myapp:hardened
trivy image myapp:hardened || true
```

### Что нужно явно показать
- base image и почему она выбрана;
- есть ли multi-stage build;
- от какого пользователя стартует контейнер;
- как изменился размер и скан-результат образа.

---

## 4.5 Lab-only проверка

Все проверки в этой главе выполняются только на своих VM, контейнерах, тестовых доменах и собственных сервисах.

- собери образ до и после hardening и сравни список слоев;
- проверь, что контейнер запускается не от root;
- зафиксируй, что в финальный образ не попадают build secrets и ненужные инструменты.

---

## 4.6 Типовые ошибки

- использовать latest и не обновлять образ осознанно;
- тащить build tooling в runtime;
- запускать контейнер от root просто по умолчанию;
- не иметь .dockerignore.

---

## 4.7 Чеклист главы

- [ ] У Dockerfile есть предсказуемая base image стратегия
- [ ] Runtime контейнер запускается от не-root пользователя
- [ ] Лишние зависимости убраны из финального образа
- [ ] Образ проверяется сканером и обновляется по плану
