# Глава 0: Боль ручного деплоя

```
1. Написал код
2. git push
3. SSH на сервер
4. docker build
5. docker stop + docker run
6. Проверить
```

9 шагов. Нет истории. Нет тестов. Откат = повторить всё.

```mermaid
flowchart LR
    code["Написал код"] --> push["git push"]
    push --> ssh["SSH на сервер"]
    ssh --> build["docker build"]
    build --> restart["docker stop\n+ docker run"]
    restart --> check["Проверить\nвручную"]
    check -.->|"что-то сломалось"| ssh

    style code fill:#2d2d2d,color:#fff
    style ssh fill:#7d6608,color:#fff
    style restart fill:#7d6608,color:#fff
    style check fill:#6e2f1a,color:#fff
```

Каждый шаг делается руками, нигде не фиксируется, и при ошибке цикл повторяется заново. Дальше в книге мы автоматизируем всю эту цепочку.

**Цель:** 0 ручных шагов.

---

## 📋 Чеклист

- [ ] Я вижу проблему ручного деплоя

**Переходи к Главе 1 — CI пайплайн.**
