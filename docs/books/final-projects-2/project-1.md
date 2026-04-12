# Проект 1: Production Python App

---

## Архитектура

```
Developer → git push → GitHub Actions
    ├── pytest
    ├── docker build → ghcr.io
    └── update image tag в infra-repo
            ↓
        ArgoCD → K8s кластер
            ├── Deployment (2 реплики, HPA: 2-8)
            ├── Service + Ingress (HTTPS)
            ├── StatefulSet: PostgreSQL + PVC
            └── ConfigMap + Secret

    Prometheus + Grafana + Loki
        ├── RED метрики
        ├── Алерты в Telegram
        └── Логи всех Pod'ов
```

---

## Playbook

### Фаза 1: Инфраструктура

```bash
# 1. Terraform: создать сервер
cd infra/terraform
terraform init && terraform apply

# 2. Ansible: настроить
cd infra/ansible
ansible-playbook setup-server.yml

# 3. Проверить
kubectl get nodes       # Ready
argocd app list         # доступно
```

### Фаза 2: Мониторинг

```bash
# 1. Установить стек
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

# 2. Grafana через Ingress
kubectl get ingress -n monitoring

# 3. Алерты в Telegram
# Настроить values.yaml alertmanager с telegram_configs
helm upgrade monitoring ... -f values.yaml
```

### Фаза 3: Приложение

```bash
# 1. Создать ArgoCD Application
kubectl apply -f argocd/myapp.yaml -n argocd

# 2. ArgoCD синхронизирует
argocd app sync myapp

# 3. Проверить
curl https://myapp.ru/health    # 200
kubectl get pods -n prod        # Running
```

### Фаза 4: CI/CD

```bash
# 1. Настроить GitHub Actions secrets
# GITHUB_TOKEN, SERVER_HOST, SSH_PRIVATE_KEY

# 2. Push → деплой
git commit --allow-empty -m "test"
git push

# 3. Наблюдать
# GitHub Actions: зелёный
# ArgoCD: Synced
# curl https://myapp.ru/health → 200
```

### Финальный тест

```bash
terraform destroy
sleep 300
time (terraform apply && ansible-playbook setup-server.yml)
# Всё восстановлено за < 30 минут
```

---

## Checklist (20 пунктов)

### Функциональность (7)
- [ ] `curl https://myapp.ru` → 200 OK
- [ ] SSL сертификат валидный
- [ ] `/health` → `{"status":"ok"}`
- [ ] `kubectl delete pod myapp-xxx` → поднялся < 30 сек
- [ ] `git push` → деплой < 10 минут
- [ ] `helm upgrade` → без даунтайма
- [ ] Метрики в Grafana видны

### Надёжность (7)
- [ ] HPA: при нагрузке реплики выросли (`kubectl get hpa`)
- [ ] БД: удалить Pod → данные сохранились
- [ ] ArgoCD selfHeal: `kubectl scale deployment myapp --replicas=5` → вернулось к 2
- [ ] Алерт в Telegram при недоступности
- [ ] Алерт в Telegram при error rate
- [ ] `terraform destroy && apply` → восстановление < 30 мин
- [ ] Liveness/Readiness probes работают

### Безопасность (6)
- [ ] PostgreSQL не доступна снаружи кластера
- [ ] Секреты не в Git (проверь `git log`)
- [ ] Образ без root (`USER nonroot` в Dockerfile)
- [ ] Resources limits заданы (`kubectl describe pod`)
- [ ] NetworkPolicy: только api → postgres
- [ ] Образы с конкретными тегами (не `latest`)
