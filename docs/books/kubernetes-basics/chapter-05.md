# Глава 5: Volume и PersistentVolume

> **Запомни:** Данные в Pod временные. PVC = постоянный диск который переживает пересоздание Pod.

---

## 5.1 PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pgdata
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### Использовать в Pod

```yaml
volumes:
- name: pgdata
  persistentVolumeClaim:
    claimName: pgdata
containers:
- name: postgres
  volumeMounts:
  - name: pgdata
    mountPath: /var/lib/postgresql/data
```

---

## 5.2 Проверить

```bash
kubectl get pvc
# pgdata  Bound  1Gi

kubectl get pv
# pvc-xxx  1Gi  Bound
```

---

## 📝 Упражнения

### Упражнение 5.1: PVC
**Задача:**
1. Создай PVC и Deployment с PostgreSQL
2. Наполни данными
3. Удали Pod → новый поднялся → данные сохранились?

---

## 📋 Чеклист главы 5

- [ ] Я могу создать PVC
- [ ] Я могу подключить PVC к Pod
- [ ] Данные сохраняются при пересоздании Pod

**Всё отметил?** Переходи к Главе 6 — Namespace.
