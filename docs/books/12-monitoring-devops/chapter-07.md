# Глава 7: LogQL — поиск по логам

---

## 7.1 Основы

```
# Все логи из namespace
{namespace="default"}

# С фильтром по тексту
{namespace="default"} |= "ERROR"

# Regexp
{namespace="default"} |~ "error|exception|failed"

# JSON парсинг
{container="app"} | json | level="error"
```

---

## 7.2 Корреляция с метриками

В Grafana:
1. Увидел спайк ошибок на дашборде (метрика)
2. Кликнул на временной отрезок
3. Открылись логи из Loki за это время
4. Нашёл причину: "ERROR: connection pool exhausted"

---

## 📋 Чеклист

- [ ] Могу написать LogQL запрос
- [ ] Вижу логи в Grafana
- [ ] Коррелирую метрики с логами

**Книга 12 завершена!**
