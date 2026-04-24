# Часть 3: Security Engineering — архитектура серии

> От домашней лаборатории до архитектурных решений для VPS, small business и enterprise.

---

## Зачем нужна эта часть

Первые две части курса учат поднимать, сопровождать и автоматизировать инфраструктуру. Третья часть учит другой задаче: как защищать системы, как понимать логику атакующего и как безопасно проверять свою защиту в собственной лаборатории.

Это не курс для offensive-эксплуатации чужих систем. Это defensive security трек:

- защита Linux, сети, web, cloud и container окружений;
- безопасная эмуляция атак в своих VM и контейнерах;
- чтение логов, сетевого трафика и событий защиты;
- итоговые проекты, где защита должна быть доказана проверками.

---

## Целевая аудитория

- программист или DevOps-инженер;
- поверхностно знаком с сетью;
- умеет работать в Linux, но не строил security-архитектуру;
- хочет понимать не только "как включить защиту", но и "от чего она защищает";
- хочет дойти от домашней lab до более серьёзной инфраструктуры.

---

## Главные ограничения и правила

1. Только свои стенды, свои VM, свои контейнеры, свои тестовые VPS и свои домены.
2. Никаких destructive-упражнений на production.
3. Никаких инструкций по реальному вредоносному ПО, ботнетам, ransomware-as-a-service и атаке чужих систем.
4. Offensive-материал допустим только в трёх форматах:
   - безопасная проверка своей защиты;
   - lab-only демонстрации в изолированной среде;
   - теория тактик, техник и процедур атакующего.
5. Перед каждой опасной главой рекомендуется snapshot/backup.

---

## Сквозная идея части

Каждая книга отвечает на одну и ту же цепочку вопросов:

1. Что за угроза?
2. Как она выглядит в реальном мире?
3. Что увидит защитник в логах, метриках и трафике?
4. Как построить защиту слоями?
5. Как безопасно проверить, что защита реально работает?
6. Как это меняется при переходе от home lab к VPS, small business и enterprise?

---

## Структура части

| Модуль | Название | Для кого | Главный результат |
|---|---|---|---|
| 15 | Защита от внешних атак | Для всех | Публичный Linux-сервер защищён на уровне периметра, SSH, firewall, reverse proxy, WAF/IDS/IPS basics |
| 16 | Web Security для программиста | Для всех | Программист понимает и закрывает основные web-риски в коде и конфигурации |
| 17 | Сетевая защита и защитные устройства | Дом / VPS / small business / enterprise | Понимание edge firewall, UTM/NGFW, DMZ, VLAN, VPN, IDS/IPS и сетевой сегментации |
| 18 | Cloud, Docker и Kubernetes Security | VPS / cloud / enterprise | Защита образов, secrets, IAM, registry, container runtime и K8s базового уровня |
| 19 | Detection, Monitoring, Incident Response | Для всех | Читатель умеет собирать сигналы, реагировать на инциденты и проверять восстановление |
| 20 | Attacker Mindset для защитника | Для всех | Читатель понимает kill chain и умеет делать безопасные lab-only демонстрации |
| 21 | Security Architecture: от дома до организации | VPS / small business / enterprise | Читатель видит целостную архитектуру защиты и умеет выбирать решения по масштабу |

---

## Книги подробнее

### Модуль 15: Защита от внешних атак

Темы:
- поверхность атаки;
- router/firewall/security gateway;
- Linux hardening;
- SSH hardening;
- fail2ban, CrowdSec;
- reverse proxy, rate limiting;
- WAF basics;
- IDS/IPS basics;
- anti-DDoS layers;
- итоговый проект: защищённый публичный сервер.

### Модуль 16: Web Security для программиста

Темы:
- trust boundaries;
- auth/session/password reset;
- SQLi, XSS, SSRF, CSRF, file upload, deserialization, secrets;
- secure headers;
- безопасная конфигурация reverse proxy;
- безопасные демонстрации на локальных стендах;
- итоговый проект: привести web-приложение к defensible baseline.

### Модуль 17: Сетевая защита и защитные устройства

Темы:
- аппаратные firewall и UTM;
- NGFW, IDS/IPS, WAF, reverse proxy;
- DMZ, сегментация, VLAN;
- VPN site-to-site и remote access;
- DNS security;
- tcpdump, Wireshark, Suricata, Zeek basics;
- итоговый проект: gateway + DMZ + app server.

### Модуль 18: Cloud, Docker и Kubernetes Security

Темы:
- security groups, IAM, bastion;
- CDN/WAF/anti-DDoS layers;
- Docker image hardening;
- supply chain security;
- secret management;
- container runtime isolation;
- K8s policy basics;
- итоговый проект: защищённый cloud/container стек.

### Модуль 19: Detection, Monitoring, Incident Response

Темы:
- asset inventory;
- logging pipeline;
- Wazuh/EDR-style visibility;
- алерты и triage;
- IR workflow;
- forensic basics;
- ransomware resilience и backup verification;
- итоговый проект: attack -> detect -> contain -> recover.

### Модуль 20: Attacker Mindset для защитника

Темы:
- reconnaissance;
- initial access;
- privilege escalation theory;
- persistence theory;
- lateral movement theory;
- exfiltration theory;
- безопасные lab-only демонстрации;
- итоговый проект: защитный разбор kill chain на своём стенде.

### Модуль 21: Security Architecture — от дома до организации

Темы:
- reference architectures;
- zero trust concepts;
- bastion, MFA, SSO, VPN;
- central logging and policy;
- supply chain governance;
- выбор между home/VPS/small business/enterprise pattern;
- интеграция Linux-инфраструктуры в более крупую организацию;
- Active Directory только как внешняя зависимость и интеграционный контекст, без Windows hands-on.

---

## Общий формат каждой книги

Каждая книга должна быть самостоятельной и подробной, даже если местами повторяет то, что уже было в других книгах.

Обязательные элементы:

- `book.md` — обзор книги;
- `chapter-00.md` — карта пути и threat model;
- 8-10 глав основного материала;
- `appendix-a.md`, `appendix-b.md` — шпаргалки, reference, конфиги, команды;
- `practice-cheatsheet.md` или `exercises.md`;
- итоговый проект;
- финальный чеклист;
- стартовая точка;
- указание, кому особенно полезна глава: дом / VPS / small business / enterprise / всем.

---

## Формат упражнений

Безопасный паттерн:

1. Построй защиту.
2. Сними baseline.
3. Запусти безопасную проверку на своём стенде.
4. Посмотри логи, события, алерты.
5. Исправь конфигурацию.
6. Повтори тест.

Примеры допустимых проверок:

- `nmap` по своим адресам;
- тестовый brute-force против своей lab-VM;
- `curl`, `wrk`, `ab`, `hey` для нагрузки;
- EICAR для проверки антивирусной цепочки;
- intentionally vulnerable demo app в локальной сети;
- policy violation в Docker/K8s lab;
- восстановление из backup и rollback.

---

## Итоговые проекты

У первой книги обязательно должны быть три варианта итогового проекта:

1. один защищённый публичный Linux-сервер;
2. gateway + DMZ + app server;
3. лаборатория со сценариями атак и доказательством работы защиты.

Для остальных книг нужен минимум один итоговый проект и, где уместно, 1-2 альтернативных сценария под другой масштаб.

---

## Что пока вне этой части

- полноценный Windows/AD hands-on трек;
- red-team offensive exploitation course;
- разработка вредоносного ПО;
- атаки на чужую инфраструктуру.

AD можно упоминать как часть enterprise-контекста, но не строить на нём практику без отдельного Windows-модуля.
