# Глава 6: Namespace — изоляция окружений

> **Запомни:** Namespace = виртуальный кластер. Dev и prod в одном кластере, не мешают друг другу.

---

## 6.1 Создать

```bash
kubectl create namespace dev
kubectl create namespace prod
```

---

## 6.2 Использовать

```bash
kubectl apply -f deployment.yaml -n dev
kubectl get pods -n dev
```

Или установить по умолчанию:

```bash
kubectl config set-context --current --namespace=dev
```

---

## 6.3 Изоляция

Dev: `myapp-svc` → `myapp-svc.dev.svc.cluster.local`
Prod: `myapp-svc` → `myapp-svc.prod.svc.cluster.local`

Разные namespace — разные сервисы с одинаковыми именами.

---

## 📝 Упражнения

### Упражнение 6.1: Namespace
**Задача:**
1. Создай dev и prod namespace
2. Задеплой приложение в оба с разными ConfigMap
3. Убедись что изолированы

---

## 📋 Чеклист главы 6

- [ ] Я могу создать namespace
- [ ] Я могу деплоить в namespace
- [ ] Я понимаю изоляцию между namespace

**Всё отметил?** Переходи к Главе 7 — Деплой Python-приложения.
