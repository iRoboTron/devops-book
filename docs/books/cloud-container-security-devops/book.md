# Cloud, Docker и Kubernetes Security: IAM, secrets, images и runtime

> Книга 18: связать cloud perimeter, контейнеры, secrets и runtime-защиту в один практический security-подход.

---

## Оглавление

### Подготовка

- [**Глава 0: Threat model cloud и container среды**](chapter-00.md)
  - Активы, trust boundaries, control plane, registry и runtime.

### Часть 1: Cloud и доступ

- [**Глава 1: Cloud perimeter и публичные сервисы**](chapter-01.md)
  - Security groups, bastion, private/public зоны и внешний слой защиты.
- [**Глава 2: IAM и минимальные права**](chapter-02.md)
  - Роли, ключи, service accounts и цена избыточных прав.
- [**Глава 3: Secrets и конфиденциальные данные**](chapter-03.md)
  - От `.env` до secret manager, ротации и CI secrets.

### Часть 2: Контейнеры и цепочка поставки

- [**Глава 4: Docker image hardening**](chapter-04.md)
  - Base image, non-root, scanners, размер образа и SBOM basics.
- [**Глава 5: Runtime security**](chapter-05.md)
  - Capabilities, readonly FS, seccomp/AppArmor и ограничения на контейнере.
- [**Глава 6: Registry и supply chain**](chapter-06.md)
  - Теги, digests, provenance, signing concepts и доверенная сборка.
- [**Глава 7: Kubernetes security basics**](chapter-07.md)
  - RBAC, namespaces, pod security, network policies, ingress.
- [**Глава 8: Практика безопасных проверок**](chapter-08.md)
  - Scan -> fix -> redeploy и controlled policy violations только в своей lab.

### Часть 3: Финал

- [**Глава 9: Итоговый проект**](chapter-09.md)
  - Hardened cloud/container стек с проверяемым baseline.

### Приложения

- [**Приложение A: Шпаргалка и быстрые команды**](appendix-a.md)
- [**Приложение B: Лаборатория и reference-manifests**](appendix-b.md)

---

## Баланс книги

- 30% — cloud perimeter, IAM и secrets;
- 40% — контейнеры, registry и runtime;
- 20% — Kubernetes baseline;
- 10% — итоговый проект и проверка.

---

## Главный результат

Читатель должен перестать думать о контейнерах как о "просто удобной упаковке" и увидеть:
- где утекают секреты;
- почему root в контейнере всё ещё плохая идея;
- как supply chain превращается в security-вопрос;
- как cloud и container security сходятся в одном рабочем baseline.

---

*Cloud, Docker и Kubernetes Security: IAM, secrets, images и runtime — Курс Security Engineering, Модуль 18*
