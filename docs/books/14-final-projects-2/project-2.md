# Проект 2: Микросервисы

---

## Архитектура

```
Интернет → Ingress
    ├── /api   → api (FastAPI, 3 реплики)
    │               │ HTTP → worker
    └── /        → frontend (static, 2 реплики)

worker → PostgreSQL (StatefulSet)
       → Redis (StatefulSet, очередь)

Мониторинг: Prometheus scrapes all 3 services
```

---

## Стартовая точка

Тип проекта: **продолжение проекта 1**.

Это не чистый кластер. Ты берёшь платформу из проекта 1 и раскладываешь приложение на несколько сервисов: `api`, `worker`, `frontend`, PostgreSQL и Redis.

До начала должно быть:
- проект 1 пройден или восстановлен;
- K8s-кластер работает;
- ArgoCD доступен;
- monitoring stack установлен;
- namespace `prod` готов;
- Ingress и домен работают;
- есть infra-репозиторий с Helm charts или K8s-манифестами.

Если хочешь пройти этот проект отдельно, сначала подними минимальную базу проекта 1: Terraform + Ansible + K8s + ArgoCD + monitoring. Без этого ApplicationSet, Ingress и мониторинг будут непонятно к чему подключать.

---

## Playbook

### Фаза 1: Базовые сервисы

```bash
# 1. PostgreSQL
kubectl apply -f k8s/postgres/

# 2. Redis
kubectl apply -f k8s/redis/

# 3. Проверить
kubectl exec -it redis-0 -- redis-cli ping     # PONG
kubectl exec -it postgres-0 -- psql -U postgres -c "SELECT 1"
```

### Фаза 2: Сервисы через ArgoCD ApplicationSet

```yaml
# argocd/appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-services
spec:
  generators:
  - list:
      elements:
      - service: api
        path: helm/api
      - service: worker
        path: helm/worker
      - service: frontend
        path: helm/frontend
  template:
    metadata:
      name: "{{service}}"
    spec:
      source:
        repoURL: https://github.com/user/app-infra.git
        targetRevision: main
        path: "{{path}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: prod
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

```bash
kubectl apply -f argocd/appset.yaml -n argocd
argocd app list
```

### Фаза 3: e2e тест

```bash
# Запрос через api → обработан worker → результат в postgres
curl -X POST https://myapp.ru/api/task -d '{"data":"test"}'
kubectl exec -it postgres-0 -- psql -U postgres -c "SELECT * FROM tasks;"
```

### Финальный тест

```bash
# Убить worker → задачи в очереди → worker поднялся → обработал
kubectl delete pod worker-0
kubectl logs worker-0 -f

# Обновить api → worker и frontend не перезапускаются
kubectl set image deployment/api api=new-image:tag
kubectl rollout status deployment/api
```

---

## Checklist (20 пунктов)

### Функциональность (7)
- [ ] Все 3 сервиса через Ingress доступны
- [ ] api → worker коммуникация работает
- [ ] worker → postgres запись работает
- [ ] Redis очередь: задачи не теряются при рестарте worker
- [ ] Независимый деплой: обновить api без worker/frontend
- [ ] Метрики всех 3 сервисов в Grafana
- [ ] Логи всех 3 сервисов в Loki

### Надёжность (7)
- [ ] Убить один сервис → остальные работают
- [ ] HPA для api (публичный трафик)
- [ ] readinessProbe: сервис не получает трафик до готовности
- [ ] Алерт если любой сервис недоступен > 2 мин
- [ ] Откат любого сервиса через ArgoCD
- [ ] Graceful shutdown: не теряет запросы
- [ ] `terraform destroy && apply` → < 40 мин

### Безопасность (6)
- [ ] worker не доступен из интернета (только через api)
- [ ] postgres доступен только из namespace приложения
- [ ] Каждый сервис под своим ServiceAccount
- [ ] Нет privileged контейнеров
- [ ] Resource limits для каждого сервиса
- [ ] Все образы с конкретными тегами
