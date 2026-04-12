# K8s Advanced — Приложения

---

## A: Шпаргалка

| Команда | Назначение |
|---------|-----------|
| `kubectl get ingress` | Ingress правила |
| `kubectl get hpa` | HPA статус |
| `kubectl top pods` | CPU/RAM Pod'ов |
| `kubectl get statefulset` | StatefulSet |
| `kubectl get networkpolicy` | NetworkPolicy |
| `kubectl auth can-i get pods --as=sa` | Проверка RBAC |
| `helm template NAME ./chart` | Показать YAML |
| `helm install NAME ./chart` | Установить |
| `helm upgrade NAME ./chart` | Обновить |
| `helm rollback NAME 1` | Откат |
| `helm uninstall NAME` | Удалить |

## B: Готовые манифесты

### Ingress + TLS
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  tls:
  - hosts: [myapp.ru]
    secretName: myapp-tls
  rules:
  - host: myapp.ru
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-svc
            port: {number: 80}
```

### HPA
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target: {type: Utilization, averageUtilization: 70}
```

### NetworkPolicy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-postgres
spec:
  podSelector:
    matchLabels: {app: postgres}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: api}
    ports: [{port: 5432}]
```

## C: Диагностика

| Ошибка | Причина | Решение |
|--------|---------|---------|
| Ingress 502 | Service не существует | Проверь имя и порт Service |
| HPA не масштабирует | Нет resource requests | Добавь requests в Deployment |
| StatefulSet Pending | Нет StorageClass | Проверь `kubectl get storageclass` |
| NetworkPolicy не работает | CNI не поддерживает | Установи Calico/Cilium |
| `helm template` ошибка | Ошибка в шаблоне | Проверь отступы и `{{ }}` |
