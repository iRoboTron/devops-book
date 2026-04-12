# Глава 8: kubectl шпаргалка (справочник)

> Обращайся по необходимости. Не читай подряд.

---

| Команда | Назначение |
|---------|-----------|
| `kubectl get pods` | Список Pod'ов |
| `kubectl get pods -o wide` | С IP и Node |
| `kubectl get all -n NS` | Всё в namespace |
| `kubectl describe pod NAME` | Детали + Events |
| `kubectl logs NAME` | Логи |
| `kubectl logs -f NAME` | Следить за логами |
| `kubectl exec -it NAME -- bash` | Войти внутрь |
| `kubectl apply -f FILE` | Применить манифест |
| `kubectl delete -f FILE` | Удалить по манифесту |
| `kubectl port-forward pod/NAME 8080:8000` | Пробросить порт |
| `kubectl rollout status deploy/NAME` | Статус обновления |
| `kubectl rollout history deploy/NAME` | История ревизий |
| `kubectl rollout undo deploy/NAME` | Откат |
| `kubectl scale deploy NAME --replicas=5` | Масштабировать |
| `kubectl get events --sort-by='.lastTimestamp'` | События |
| `kubectl config set-context --current -n NS` | Сменить namespace |

---

# Глава 9: Rolling update и откат

> **Запомни:** Rolling update = обновление без даунтайма. K8s обновляет Pod'ы по одному.

---

## 9.1 Обновить

```bash
kubectl set image deployment/myapp app=ghcr.io/user/myapp:v2
kubectl rollout status deployment/myapp
```

## 9.2 История

```bash
kubectl rollout history deployment/myapp
```

## 9.3 Откат

```bash
kubectl rollout undo deployment/myapp
kubectl rollout undo deployment/myapp --to-revision=2
```

---

# Глава 10: Ресурсы — limits, requests

> **Запомни:** Pod без limits съест всю ноду. Всегда ставь resources.

---

## 10.1 requests vs limits

```yaml
resources:
  requests:
    memory: "64Mi"    # зарезервировать (для Scheduler)
    cpu: "50m"
  limits:
    memory: "128Mi"   # максимум (превышение = OOM kill)
    cpu: "100m"
```

## 10.2 OOM kill

Pod превысил memory limits → K8s убил и перезапустил.

```bash
kubectl get pods
# myapp-xxx  OOMKilled  →  Restarting
```

---

## 📋 Чеклист глав 8-10

- [ ] Я знаю основные команды kubectl
- [ ] Я могу сделать rolling update
- [ ] Я могу откатить к предыдущей версии
- [ ] Я ставлю resources requests и limits каждому Pod
- [ ] Я понимаю что будет при OOM kill

**Всё отметил?** Книга 10 завершена!
