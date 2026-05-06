# Глава 6: Скрипты на bash и Python

> **Цель:** использовать локальную модель как часть автоматизации.

---

## 6.1 Bash-скрипт

Создай `ask-ollama.sh`:

```bash
#!/bin/bash
set -euo pipefail

MODEL="${1:-llama3.2:3b}"
PROMPT="${2:-Объясни что такое Linux service}"

curl -sf -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL\", \"prompt\": \"$PROMPT\", \"stream\": false}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["response"])'
```

Запуск:

```bash
chmod +x ask-ollama.sh
./ask-ollama.sh llama3.2:3b "Что такое Docker?"
```

# Пример вывода:
```
Docker — это платформа для запуска приложений в изолированных контейнерах.
Контейнер содержит само приложение и все его зависимости, что позволяет
запускать его одинаково на любом сервере независимо от окружения.
Это удобно для разработки, тестирования и деплоя: "собери один раз — запускай везде".
```

Ограничение: такой простой JSON ломается, если prompt содержит сложные кавычки. Для серьёзной автоматизации удобнее Python.

> **Аналогия:** скрипт `ask-ollama.sh` — это как ярлык на рабочем столе. Один раз написал, дальше просто вызываешь с разными вопросами, не вспоминая длинную curl-команду.

---

## 6.2 Python-скрипт

```python
import requests


def ask_ollama(prompt: str, model: str = "llama3.2:3b") -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


if __name__ == "__main__":
    print(ask_ollama("Объясни разницу между Docker image и container"))
```

Установка зависимости:

```bash
python3 -m pip install requests
```

Запуск:

```bash
python3 script.py
```

# Пример вывода:
```
Docker image — это неизменяемый шаблон, из которого создаются контейнеры.
Представьте image как кулинарный рецепт, а container — как готовое блюдо,
приготовленное по этому рецепту. Из одного рецепта (image) можно приготовить
много блюд (контейнеров), каждое из которых работает независимо. Image хранится
на диске и не меняется, а контейнер живёт в памяти и может быть остановлен,
перезапущен или удалён.
```

---

## 6.3 Реальные сценарии

| Сценарий | Что отправляем | Риск |
|---|---|---|
| кратко объяснить лог | последние 100 строк | лог может содержать IP, токены, email |
| проверить nginx-конфиг | конфиг без секретов | можно случайно отправить домены и пути |
| сгенерировать commit message | `git diff` | diff может содержать секреты |
| сделать черновик инструкции | описание задачи | низкий риск |

Перед отправкой логов и конфигов очищай секреты.

---

## 6.4 Практика

Сделай скрипт `explain-log.py`, который читает тестовый файл `sample.log`, отправляет его в модель и просит объяснить ошибки простым языком.

Проверка: скрипт не требует интернета, работает через `localhost:11434` и не отправляет реальные секреты.

---

> **Если что-то пошло не так:**
>
> **Симптом:** Python-скрипт падает с ошибкой `requests.exceptions.ConnectionError`.
>
> Полный вид ошибки:
> ```
> requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=11434):
> Max retries exceeded with url: /api/generate
> (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x...>:
> Failed to establish a new connection: [Errno 111] Connection refused'))
> ```
>
> Это значит, что Ollama не запущен или слушает на другом адресе.
>
> Диагностика:
> ```bash
> systemctl status ollama
> curl http://localhost:11434/api/tags
> ```
>
> Если Ollama запущен через Docker — проверь что порт проброшен:
> ```bash
> docker ps | grep ollama
> # Должно быть: 127.0.0.1:11434->11434/tcp
> ```
>
> **Симптом:** скрипт висит дольше 120 секунд без ответа.
>
> Модель может быть перегружена или слишком большой. Добавь обработку таймаута:
> ```python
> try:
>     response = requests.post(..., timeout=120)
> except requests.exceptions.Timeout:
>     print("Ошибка: модель не ответила за 120 секунд. Попробуй меньшую модель.")
>     raise SystemExit(1)
> ```
