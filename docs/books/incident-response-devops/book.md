# Detection, Monitoring и Incident Response: Сигналы, triage и восстановление

> Книга 19: защита не заканчивается на настройке firewall. Нужно ещё заметить проблему, локализовать её и восстановиться.

---

## Оглавление

### Подготовка

- [**Глава 0: Что считать инцидентом**](chapter-00.md)
  - Event, alert, incident, severity и цена неправильной реакции.

### Часть 1: Сигналы

- [**Глава 1: Логи как сырьё для защиты**](chapter-01.md)
  - Auth, web, app, audit и centralization basics.
- [**Глава 2: Метрики и алерты**](chapter-02.md)
  - Golden signals, actionability и борьба с alert fatigue.
- [**Глава 3: Host-level detection**](chapter-03.md)
  - Baseline deviations, file integrity, подозрительные процессы и события.

### Часть 2: Реакция

- [**Глава 4: Triage и быстрые проверки**](chapter-04.md)
  - Что проверять первым и как не ломать доказательства и сервис одновременно.
- [**Глава 5: Recovery и проверка восстановления**](chapter-05.md)
  - Rebuild, rollback, key rotation и проверка backup discipline.
- [**Глава 6: Ransomware resilience без вредоносной практики**](chapter-06.md)
  - Immutable-like идеи, blast radius reduction и realistic backup drills.
- [**Глава 7: Forensics basics для инженера**](chapter-07.md)
  - Что собирать, что сохранять и где проходит предел разумного.
- [**Глава 8: Практика incident drills**](chapter-08.md)
  - Tabletop и controlled detect -> contain -> recover сценарии.

### Часть 3: Финал

- [**Глава 9: Итоговый проект**](chapter-09.md)
  - Полный цикл сигнала, triage, containment, recovery и postmortem.

### Приложения

- [**Приложение A: Шпаргалка и быстрые команды**](appendix-a.md)
- [**Приложение B: Лаборатория и IR-шаблоны**](appendix-b.md)

---

## Баланс книги

- 35% — сигналы и видимость;
- 35% — triage и recovery;
- 20% — controlled drills;
- 10% — итоговый проект и шаблоны.

---

## Главный результат

После этой книги читатель должен уметь не просто заметить тревогу, а провести инженерную реакцию:
- понять, что произошло;
- не паниковать и не усугубить ситуацию;
- локализовать проблему;
- восстановить сервис;
- зафиксировать уроки после инцидента.

---

*Detection, Monitoring и Incident Response: Сигналы, triage и восстановление — Курс Security Engineering, Модуль 19*
