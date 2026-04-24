# Инструкция для ИИ-агента: Модуль 18 — Cloud, Docker и Kubernetes Security

> **Это четвёртая книга части 3.**
> Она должна связать защиту хоста, cloud-периметра и container стека.

---

## Контекст проекта

Читатель уже знает, что у него есть VPS, Docker, registry, возможно Kubernetes. Он хочет понять:

- где в cloud появляются новые риски;
- чем опасны лишние IAM права;
- как hardenить Docker image и runtime;
- как защищать Kubernetes на базовом уровне;
- как это проверять безопасно.

---

## Что за книга

**Название:** "Cloud, Docker и Kubernetes Security: IAM, secrets, images и runtime"

**Каталог:** `18-cloud-container-security-devops`

**Для кого особенно полезна:**
- VPS;
- cloud;
- команды с Docker/Kubernetes;
- small business и enterprise.

**Объём:** 170-220 страниц

---

## Структура книги

### Глава 0: Threat model cloud и container среды
- control plane;
- account compromise;
- leaked secrets;
- public buckets/registry;
- lateral movement через container stack.

### Глава 1: Cloud perimeter
- security groups;
- NACL basics;
- bastion/jump host;
- private vs public subnet;
- CDN/WAF/anti-DDoS layers.

### Глава 2: IAM и минимальные права
- least privilege;
- service accounts;
- access keys;
- rotation;
- типовые ошибки.

### Глава 3: Secrets
- `.env` vs vault-like systems;
- secret rotation;
- CI secrets;
- runtime exposure;
- как не тащить секреты в image.

### Глава 4: Docker image hardening
- base image choice;
- non-root user;
- image size;
- scanners (`trivy`, `grype`, `syft`);
- SBOM basics.

### Глава 5: Runtime security
- capabilities;
- read-only FS;
- seccomp/AppArmor;
- network boundaries;
- container breakout theory.

### Глава 6: Registry и supply chain
- image signing concepts;
- pinned tags/digests;
- provenance basics;
- CI/CD trust chain.

### Глава 7: Kubernetes security basics
- namespaces;
- RBAC;
- network policies;
- pod security;
- ingress security;
- secrets and config.

### Глава 8: Безопасные проверки
- scan образов;
- policy violations;
- intentionally weak manifest in lab;
- public service exposure review.

### Глава 9: Итоговый проект
- hardened container/cloud stack;
- scan -> fix -> redeploy -> verify.

---

## Итоговый проект

Основной вариант:
- cloud VM или managed cluster;
- приложение в Docker/K8s;
- secrets вынесены;
- image scanning;
- least privilege;
- проверяемое сетевое ограничение;
- документированный rollback и recovery.

---

## Особое требование

Не делай книгу "только про Kubernetes". Она должна быть полезна и человеку с одним VPS и Docker Compose, и команде с cloud/K8s.
