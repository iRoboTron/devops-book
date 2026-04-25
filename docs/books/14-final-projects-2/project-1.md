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

## Стартовая точка

Тип проекта: **базовый capstone DevOps 2.0 с нуля**.

Этот проект создаёт фундамент для проектов 2-4. Начинай с чистого infra-репозитория и тестового облачного окружения, где можно безопасно создавать и удалять ресурсы через Terraform.

До начала должно быть:
- пройдены модули 8-13;
- аккаунт облачного провайдера для Terraform;
- SSH-ключи;
- домен или поддомен для Ingress;
- репозитории `app-code` и `app-infra`;
- локально установлены `terraform`, `ansible`, `kubectl`, `helm`, `argocd`.

Если у тебя уже есть кластер из учебных глав, можешь использовать его только как временную лабораторию. Для финального зачёта лучше поднять инфраструктуру заново из кода, чтобы доказать восстановление через `terraform apply && ansible-playbook`.

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

```bash
# Результат фазы: всё запущено
kubectl get nodes                               # все узлы в Ready
argocd app list                                 # нет строк Unknown
kubectl get pods -n monitoring | grep -c Running
# Ожидаемо: 6 или больше Pod'ов в Running
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

```bash
# Результат фазы: мониторинг работает
kubectl get ingress -n monitoring
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
curl -s http://localhost:9090/-/healthy        # OK
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

```bash
# Результат фазы: приложение работает
curl -i https://myapp.ru/health
kubectl get hpa -n prod
# Ожидаемо: HTTP/1.1 200 OK и в HPA заполнена колонка TARGETS
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

Главный критерий проекта: платформу можно восстановить из кода без ручного шаманства.

```bash
# Выполни полный цикл восстановления
terraform destroy -auto-approve
terraform apply -auto-approve
ansible-playbook setup-server.yml

# Затем проверь результат
kubectl get nodes          # все Ready?
kubectl get pods -n prod   # приложение Running?
curl -i https://myapp.ru   # отвечает?
```

Если после этих команд кластер вернулся, Pod'ы приложения поднялись, а `curl` снова даёт рабочий ответ, проект действительно пройден.

---

## Сохранение состояния для проектов 2-4

После успешного финального теста сохрани foundation. Это базовое состояние понадобится для проектов 2, 3 и 4.

Если платформа работает на VM, сделай снапшот с именем:

```text
after-project-1-foundation
```

Если платформа создана через облако и Terraform, сохрани не только VM-состояние, но и инфраструктурную точку восстановления:

- git commit в `app-infra`;
- актуальный remote state Terraform;
- значения переменных Terraform и Ansible inventory;
- бэкап PostgreSQL или Velero backup, если данные нужны для следующих проектов;
- список доменов, Ingress и внешних IP.

Проекты 2 и 4 начинаются от этой foundation-платформы. Проект 3 может начинаться от проекта 1 или проекта 2, но перед ним всё равно нужна отдельная копия, потому что там будут destructive-проверки.

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
