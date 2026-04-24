# Финальные проекты — Приложения

---

## A: Общие команды проверки

```bash
# Инфраструктура
terraform apply
ansible-playbook setup-server.yml
kubectl get nodes

# Приложение
kubectl get pods -n prod
curl https://myapp.ru/health
kubectl get hpa

# Мониторинг
kubectl get pods -n monitoring
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring

# Бэкапы
pg_dump -U postgres myapp_prod | gzip > backup.sql.gz
kubectl exec -it postgres-0 -- psql -U postgres -c "SELECT 1;"

# Disaster Recovery
terraform destroy && terraform apply
argocd app rollback myapp 1
```

## B: Runbook — если что-то сломалось

### Приложение недоступно
```
1. kubectl get pods -n prod
2. kubectl describe pod myapp-xxx
3. kubectl logs myapp-xxx --tail=100
4. argocd app get myapp
5. Grafana → dashboard
6. argocd app rollback myapp 1
```

### БД недоступна
```
1. kubectl get pods -n prod | grep postgres
2. kubectl describe pod postgres-0
3. kubectl logs postgres-0 --tail=100
4. kubectl exec -it postgres-0 -- psql -U postgres
```

### Кластер не отвечает
```
1. terraform destroy
2. terraform apply && ansible-playbook setup-server.yml
3. velero restore (если есть backup)
4. ArgoCD selfHeal (если infra-repo в порядке)
```

## C: Тайминги DR

| Сценарий | Цель | Факт |
|----------|------|------|
| Pod упал | < 30 сек | ___ |
| Broken deploy | < 3 мин | ___ |
| Потеря PVC | < 10 мин | ___ |
| Потеря сервера | < 30 мин | ___ |
