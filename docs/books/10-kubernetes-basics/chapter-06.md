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

## 6.4 Системные namespace

```bash
kubectl get namespaces
```

```text
NAME               STATUS
default            Active
kube-system        Active
kube-public        Active
local-path-storage Active
```

Что это значит:

- `default` — сюда попадает всё без `-n`
- `kube-system` — системные компоненты Kubernetes
- `kube-public` — публичные служебные объекты
- `local-path-storage` — storage-провайдер в `k3s`

Не деплой своё приложение в `kube-system`.

---

## 6.5 DNS между namespace

Из одного namespace можно обратиться к сервису в другом:

```bash
curl http://myapp-svc.prod.svc.cluster.local:80
```

Формат DNS-имени:

```text
<service>.<namespace>.svc.cluster.local
```

Внутри одного namespace обычно достаточно короткого имени:

```bash
curl http://myapp-svc:80
```

---

## 📝 Упражнения

### Упражнение 6.1: Namespace
**Задача:**
1. Создай dev и prod namespace
2. Задеплой приложение в оба с разными ConfigMap
3. Убедись что изолированы

### Упражнение 6.2: DNS между namespace
**Задача:**
1. Создай сервис `myapp-svc` в `prod`
2. Из временного Pod в `dev` обратись к `myapp-svc.prod.svc.cluster.local`
3. Ответ пришёл?

---

## 📋 Чеклист главы 6

- [ ] Я могу создать namespace
- [ ] Я могу деплоить в namespace
- [ ] Я понимаю изоляцию между namespace

**Всё отметил?** Переходи к Главе 7 — Деплой Python-приложения.
