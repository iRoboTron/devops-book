# Глава 4: CI + ArgoCD — полный цикл

---

## 4.1 CI обновляет infra-repo

```yaml
# .gitlab-ci.yml (в app-code repo)
update-infra:
  stage: deploy
  image: alpine/git
  script:
    - git clone https://token@gitlab.com/user/app-infra.git
    - cd app-infra
    - sed -i "s|tag: .*|tag: $CI_COMMIT_SHA|" values.yaml
    - git commit -am "Update image to $CI_COMMIT_SHA"
    - git push
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

---

## 4.2 Полный цикл

```
git push → CI: test → build → push image
                              ↓
                    update app-infra repo
                              ↓
                    ArgoCD: обнаружил изменение
                              ↓
                    K8s: helm upgrade
```

0 ручных шагов.

---

## 📋 Чеклист

- [ ] CI обновляет image tag в infra-repo
- [ ] ArgoCD обнаруживает и синхронизирует
- [ ] 0 ручных шагов

**Переходи к Главе 5 — Progressive Delivery.**
