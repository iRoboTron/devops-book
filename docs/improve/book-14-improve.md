# Инструкция агенту: улучшение книги 14 «Финальные проекты 2»

## Контекст

```
/home/adelfos/Documents/lessons/dev-ops/docs/books/14-final-projects-2/
```

Файлы: `book.md`, `project-1.md`, `project-2.md`, `project-3.md`, `project-4.md`, `appendix-a.md`

Книга: 795 строк. Формат capstone-проектов правильный — архитектура → стартовая точка → playbook → чеклист. Книга хорошо структурирована. Нужны точечные улучшения.

**Три конкретные проблемы:**
1. В playbook нет «ожидаемого результата» после каждой фазы — читатель не знает прошёл ли он фазу
2. Проект 3 (DR) — сценарии описаны как команды, но нет ожидаемого времени и что считать успехом
3. Проект 4 — Фаза 1 ("то же что Проект 1") — без минимальной проверки

---

## Что НЕ трогать

- Архитектурные схемы
- Описания стартовых точек (хорошо написаны)
- `book.md` — не трогать, структура правильная
- Нумерацию фаз в playbook'ах

---

## Задачи по проектам

---

### Проект 1 (`project-1.md`) — Production Python App

**Добавить** в конец каждой фазы блок «Результат фазы»:

**Фаза 1 (Инфраструктура):**
```bash
# Результат фазы: всё запущено
kubectl get nodes          # Ready
argocd app list            # нет строк "Unknown"
kubectl get pods -n monitoring | grep -c Running  # >= 6
```

**Фаза 2 (Мониторинг):**
```bash
# Результат фазы: мониторинг работает
kubectl get ingress -n monitoring   # Grafana доступна
curl -s http://localhost:9090/-/healthy  # OK (после port-forward)
```

**Фаза 3 (Приложение):**
```bash
# Результат фазы: приложение работает
curl https://myapp.ru/health          # 200 OK
kubectl get hpa -n prod               # TARGETS отображается
```

**Добавить** в финальный чеклист конкретные проверочные команды:

```bash
# Главный критерий проекта: восстановление из кода
# Выполни:
terraform destroy -auto-approve
terraform apply -auto-approve
ansible-playbook setup-server.yml
# Затем:
kubectl get nodes          # Ready?
kubectl get pods -n prod   # Running?
curl https://myapp.ru      # Работает?
# Если да — проект пройден
```

---

### Проект 2 (`project-2.md`) — Микросервисы

**Добавить** в конец Фазы 1 проверку базовых сервисов:

```bash
# Результат фазы 1: PostgreSQL и Redis живые
kubectl exec -it redis-0 -- redis-cli ping      # PONG
kubectl exec -it postgres-0 -- psql -U postgres -c "\l"  # список БД
```

**Добавить** в Фазу 2 (ApplicationSet) проверку:

```bash
# После применения ApplicationSet
argocd app list
# Должны появиться: api, worker, frontend
# Все Synced + Healthy
```

**Добавить** в финальный чеклист:

```bash
# Проверить что все сервисы видят друг друга
# api → worker через очередь
kubectl logs -l app=api -n prod | grep "task sent"    # задача отправлена
kubectl logs -l app=worker -n prod | grep "task done" # задача выполнена

# Метрики всех трёх сервисов в Prometheus
# PromQL: up{job=~"api|worker|frontend"} — все = 1
```

---

### Проект 3 (`project-3.md`) — Disaster Recovery

**Главная проблема:** Сценарии описывают действие, но не фиксируют ожидаемое время и что считать успехом.

**Добавить** в каждый сценарий блок «Критерий успеха» и «Как измерить время»:

**Сценарий 1 (Pod упал):**

```bash
# Зафиксировать время начала
START=$(date +%s)
kubectl delete pod myapp-xxx
kubectl wait --for=condition=Ready pod -l app=myapp -n prod --timeout=60s
END=$(date +%s)
echo "RTO: $((END - START)) секунд"
# Критерий: < 30 секунд
```

**Сценарий 2 (Broken deploy):**

```bash
# Создать сломанный образ (несуществующий тег)
kubectl set image deployment/myapp app=ghcr.io/user/myapp:nonexistent -n prod

# Наблюдать
kubectl rollout status deployment/myapp -n prod --timeout=120s
# Должно зависнуть с ошибкой ImagePullBackOff

# Откатить
START=$(date +%s)
kubectl rollout undo deployment/myapp -n prod
kubectl rollout status deployment/myapp -n prod
END=$(date +%s)
echo "RTO: $((END - START)) секунд"
# Критерий: < 3 минуты
```

**Сценарий 3 (Потеря PVC):**

```bash
# 1. Вставить тестовые данные
kubectl exec -it postgres-0 -n prod -- \
  psql -U postgres -c "INSERT INTO test VALUES ('before-dr-test')"

# 2. Создать бэкап
kubectl exec -it postgres-0 -n prod -- \
  pg_dump -U postgres myapp > backup-$(date +%Y%m%d).sql

# 3. Удалить Pod (имитировать потерю)
kubectl delete pod postgres-0 -n prod

# 4. Восстановить из бэкапа и проверить данные
START=$(date +%s)
kubectl exec -it postgres-0 -n prod -- \
  psql -U postgres -c "SELECT * FROM test WHERE value = 'before-dr-test'"
END=$(date +%s)
echo "RPO проверен, RTO: $((END - START)) секунд"
# Критерий: данные есть (RPO=0 если PVC не удалялся), время < 10 минут
```

**Сценарий 4 (Потеря сервера):**

```bash
# ВНИМАНИЕ: выполнять только на тестовом стенде с подтверждённым бэкапом

START=$(date +%s)

# 1. Удалить инфраструктуру
terraform destroy -auto-approve

# 2. Восстановить
terraform apply -auto-approve
ansible-playbook setup-server.yml

# 3. Проверить
kubectl get nodes
kubectl get pods -n prod
curl https://myapp.ru/health

END=$(date +%s)
echo "Полное восстановление: $((END - START)) секунд (RTO = $((END - START))/60 минут)"
# Критерий: < 30 минут
```

---

### Проект 4 (`project-4.md`) — Platform Engineering

**Проблема:** Фаза 1 — "То же что Проект 1" без проверки готовности платформы.

**Добавить** в Фазу 1 минимальную проверку:

```bash
# Проверить что foundation готов перед продолжением
kubectl get nodes                     # Ready
argocd app list                       # нет Unknown
kubectl get pods -n monitoring | grep -c Running  # >= 6
curl https://myapp.ru/health         # 200 (базовое приложение работает)

echo "Foundation OK — можно начинать Platform Engineering"
```

**Добавить** в Фазу 2 (Guardrails) ожидаемый результат:

После создания ResourceQuota и LimitRange — проверить что работает:

```bash
# Попробовать создать Pod без resources (должен получить дефолты из LimitRange)
kubectl run test --image=nginx -n tenant-team --restart=Never
kubectl describe pod test -n tenant-team | grep -A5 Limits
# Должны быть выставлены дефолтные limits из LimitRange

# Попробовать превысить QuotaНомер
kubectl run quota-test --image=nginx -n tenant-team \
  --requests=cpu=9 --limits=cpu=9 --restart=Never
# Ожидаемо: Error - exceeded quota
kubectl delete pod quota-test -n tenant-team --ignore-not-found
```

**Добавить** в финальный чеклист измеримые критерии:

```bash
# Platform Engineering: критерии готовности

# 1. Developer может задеплоить новый сервис без DevOps
git clone app-template
# Поменять имя сервиса
git push → CI pipeline → ArgoCD деплой
# Без ручных шагов DevOps-инженера

# 2. Guardrails работают
kubectl run big-pod --image=nginx --requests=cpu=8 -n tenant-team
# Должен получить: Error (exceeded quota)

# 3. Мониторинг нового сервиса автоматический
# ServiceMonitor template входит в шаблон нового сервиса
# Grafana автоматически показывает новый сервис
```

---

### Appendix A (`appendix-a.md`)

Проверить содержимое. Если не содержит — добавить сводную таблицу времён восстановления:

| Сценарий | Ожидаемый RTO | Как достичь |
|----------|---------------|-------------|
| Pod упал | < 30 сек | liveness probe + Deployment replicas >= 2 |
| Broken deploy | < 3 мин | `kubectl rollout undo` или ArgoCD rollback |
| Потеря PVC | < 10 мин | pg_dump каждые 5 мин + restore скрипт |
| Потеря сервера | < 30 мин | Terraform + Ansible + GitOps |

И чеклист перед уходом в "production-режим":
- [ ] `terraform destroy && terraform apply` — проверено
- [ ] `ansible-playbook setup-server.yml` — проверено  
- [ ] pg_dump + psql restore — проверено с реальными данными
- [ ] ArgoCD rollback — выполнен хотя бы раз
- [ ] Telegram алерт — получен хотя бы раз

---

## Общий объём

Цель: 1100–1200 строк (сейчас 795). Рост за счёт проверочных команд и критериев успеха.

## Приоритет

1. Проект 3 (DR) — добавить измерение времени и критерии успеха для каждого сценария
2. Проект 1 — добавить "результат фазы" с проверочными командами
3. Проект 4 — добавить проверку готовности Foundation и критерии Platform Engineering
4. Appendix A — таблица RTO и pre-production чеклист

---

*Файл: `/home/adelfos/Documents/lessons/dev-ops/docs/improve/book-14-improve.md`*
