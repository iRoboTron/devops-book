# Глава 2: GitOps идея

---

## 2.1 Push vs Pull

```
Push:                        Pull (GitOps):
CI → SSH → кластер           Git repo ← ArgoCD → кластер
CI нужны credentials         CI не нужен доступ к кластеру
                              ArgoCD синхронизирует сам
```

---

## 2.2 Два репозитория

```
app-code/          → код, Dockerfile, тесты
app-infra/         → Helm values, K8s manifests
```

CI обновляет app-infra → ArgoCD видит → синхронизирует.

---

## 📋 Чеклист

- [ ] Понимаю разницу Push vs Pull
- [ ] Понимаю зачем два репозитория

**Переходи к Главе 3 — ArgoCD.**
