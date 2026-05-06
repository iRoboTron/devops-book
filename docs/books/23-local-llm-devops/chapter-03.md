# Глава 3: Ollama API

> **Цель:** понять, что модель можно использовать не только в чате, но и из любого скрипта через HTTP.

---

## 3.1 API как обычный web-сервис

Ollama по умолчанию слушает локальный порт `11434`.

```text
скрипт
  -> POST http://localhost:11434/api/generate
  -> Ollama
  -> модель
  -> JSON-ответ
```

Проверка доступности:

```bash
curl http://localhost:11434/api/tags
```

# Пример вывода:
```json
{
  "models": [
    {
      "name": "llama3.2:3b",
      "model": "llama3.2:3b",
      "modified_at": "2025-05-05T12:40:00.000Z",
      "size": 2019393189,
      "digest": "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72",
      "details": {
        "format": "gguf",
        "family": "llama",
        "parameter_size": "3.2B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

---

## 3.2 Генерация текста

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Объясни что такое systemd простыми словами",
    "stream": false
  }'
```

# Пример вывода:
```json
{
  "model": "llama3.2:3b",
  "created_at": "2025-05-05T12:45:00.000Z",
  "response": "systemd — это система инициализации Linux, которая запускает все процессы при загрузке операционной системы. Она управляет службами (сервисами), следит за их состоянием и перезапускает их при сбое. Если вам нужно запустить, остановить или проверить состояние программы в Linux, вы взаимодействуете с systemd через команду systemctl.",
  "done": true,
  "done_reason": "stop",
  "total_duration": 8342156000,
  "load_duration": 1234567,
  "prompt_eval_count": 18,
  "prompt_eval_duration": 512000000,
  "eval_count": 87,
  "eval_duration": 7800000000
}
```

В ответе важны поля:

| Поле | Что значит |
|---|---|
| `model` | какая модель отвечала |
| `response` | текст ответа |
| `done` | завершён ли ответ |
| `total_duration` | сколько заняло времени |
| `eval_count` | сколько токенов сгенерировано |

---

## 3.3 Chat endpoint

Для диалогов удобнее `/api/chat`:

```bash
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [
      {"role": "user", "content": "Что такое reverse proxy?"}
    ],
    "stream": false
  }'
```

# Пример вывода:
```json
{
  "model": "llama3.2:3b",
  "created_at": "2025-05-05T12:46:00.000Z",
  "message": {
    "role": "assistant",
    "content": "Reverse proxy — это сервер, который принимает запросы от клиентов и перенаправляет их к одному или нескольким внутренним серверам. Клиент не знает, какой именно внутренний сервер обработал запрос. Это используется для балансировки нагрузки, кэширования, защиты внутренней инфраструктуры и добавления HTTPS."
  },
  "done": true,
  "total_duration": 6100000000,
  "eval_count": 72
}
```

История диалога не появляется сама. Если твой скрипт хочет помнить контекст, он должен отправлять предыдущие сообщения в `messages`.

---

## 3.4 OpenAI-совместимый endpoint

Многие программы умеют работать с OpenAI API. Ollama предоставляет похожий формат:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Это не значит, что качество станет как у облачной модели. Это только похожий формат API.

---

## 3.5 Практика

Сделай три запроса:

1. список моделей через `/api/tags`;
2. простой prompt через `/api/generate`;
3. chat-запрос через `/api/chat`.

Сохрани один ответ в файл:

```bash
curl -s http://localhost:11434/api/tags > ollama-tags.json
```

Проверка: ты можешь объяснить, какой URL вызывается, какой JSON отправляется и где в ответе находится текст модели.

---

> **Если что-то пошло не так:**
>
> **Симптом:** `curl: (7) Failed to connect to localhost port 11434: Connection refused`
>
> Это значит, что Ollama не запущен.
>
> Диагностика и исправление:
> ```bash
> # Проверить статус сервиса
> systemctl status ollama
>
> # Если не запущен — запустить
> sudo systemctl start ollama
>
> # Или для Docker-варианта
> docker ps | grep ollama
> docker start ollama
> ```
>
> После запуска подождать 3-5 секунд и повторить curl.
>
> **Симптом:** curl зависает и не возвращает ответ.
>
> Это нормально, если модель ещё загружается в память. Для первого запроса к модели добавь таймаут:
> ```bash
> curl --max-time 120 -X POST http://localhost:11434/api/generate \
>   -H "Content-Type: application/json" \
>   -d '{"model": "llama3.2:3b", "prompt": "Привет", "stream": false}'
> ```
