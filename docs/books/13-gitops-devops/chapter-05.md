# Глава 5: Progressive Delivery

---

## 5.1 Canary

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 5m}
      - setWeight: 50
      - pause: {duration: 5m}
      - setWeight: 100
```

20% → 50% → 100%.

---

## 5.2 Blue-Green

```yaml
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: false
```

```bash
kubectl argo rollouts promote myapp
```

---

## 📋 Чеклист

- [ ] Понимаю Canary vs Blue-Green
- [ ] Argo Rollouts установлен

**Книга 13 завершена!**
