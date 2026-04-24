# GitOps: ArgoCD и продвинутый CI/CD

> Книга 13: GitLab CI или GitHub Actions + ArgoCD

---

## Оглавление

- [**Глава 0: Боль ручного деплоя**](chapter-00.md)
- [**Глава 1: .gitlab-ci.yml / GitHub Actions**](chapter-01.md)
- [**Глава 2: GitOps идея**](chapter-02.md)
- [**Глава 3: ArgoCD установка**](chapter-03.md)
- [**Глава 4: CI + ArgoCD**](chapter-04.md)
- [**Глава 5: Progressive Delivery**](chapter-05.md)

---

## Главная идея

```
Push (CI деплоит):         Pull (GitOps):
CI → credentials → кластер  Git → ArgoCD → кластер
CI нужны права              Кластер сам тянет
```

Git — единственный источник правды.

---

## Предварительные требования

- Пройдены Модули 1-12
- K8s кластер, Helm

---

*GitOps: ArgoCD — Курс DevOps, Модуль 13*
