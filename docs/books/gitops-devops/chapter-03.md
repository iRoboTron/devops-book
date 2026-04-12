# Глава 3: ArgoCD установка

---

## 3.1 Установка

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Или Helm:
```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd --create-namespace
```

---

## 3.2 Доступ

```bash
# UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Пароль
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# CLI
brew install argocd
argocd login localhost:8080
```

---

## 3.3 Первое Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/user/app-infra.git
    targetRevision: main
    path: helm/myapp
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```bash
kubectl apply -f application.yaml -n argocd
```

---

## 📋 Чеклист

- [ ] ArgoCD установлен
- [ ] UI доступен
- [ ] Application создано
- [ ] Auto-sync включён

**Переходи к Главе 4 — CI + ArgoCD.**
