# Архитектура для эксплуатации: как проектировать приложения, которые удобно деплоить и чинить

> Книга 29: почему одни приложения легко запускать, обновлять и диагностировать, а другие ломаются при каждом релизе.

---

## Оглавление

- [Глава 0: Почему приложение должно быть удобно эксплуатировать](chapter-00.md)
- [Глава 1: Монолит, модульный монолит и микросервисы](chapter-01.md)
- [Глава 2: Stateless и stateful](chapter-02.md)
- [Глава 3: Конфигурация и секреты](chapter-03.md)
- [Глава 4: Healthcheck, readiness и liveness](chapter-04.md)
- [Глава 5: Graceful shutdown и startup](chapter-05.md)
- [Глава 6: Миграции базы данных](chapter-06.md)
- [Глава 7: Retry, timeout и circuit breaker](chapter-07.md)
- [Глава 8: Очереди и фоновые задачи](chapter-08.md)
- [Глава 9: Логи, метрики и трассировка](chapter-09.md)
- [Глава 10: Стратегии деплоя и rollback](chapter-10.md)
- [Глава 11: Итоговый проект — operability review](chapter-11.md)
- [Приложение A: Operability cheatsheet](appendix-a.md)
- [Приложение B: Ресурсы и дальнейшее чтение](appendix-b.md)
- [**Глоссарий**](glossary.md)

---

## Главная мысль

Архитектура — это не только папки в коде и красивые схемы. Для эксплуатации архитектура отвечает на вопрос: можно ли это приложение безопасно запускать, обновлять, наблюдать и восстанавливать.

```text
хороший код, но плохая эксплуатация -> аварии, ручные шаги, страшные релизы
код + operability -> понятный запуск, логи, healthcheck, rollback, backup
```

---

## Что получится в конце

Ты сделаешь `Operability review` своего проекта:

- схему приложения;
- карту состояния;
- inventory конфигурации;
- healthcheck/readiness proposal;
- shutdown/startup checklist;
- migration checklist;
- timeout/retry policy;
- logging checklist;
- rollback plan;
- operability score по шкале 0–20.