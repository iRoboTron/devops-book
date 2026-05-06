# Приложение A: Шпаргалка команд

## Ollama

```bash
ollama list
ollama pull <model>
ollama run <model>
ollama rm <model>
curl http://localhost:11434/api/tags
```

# Пример вывода ollama list:
```
NAME              ID              SIZE      MODIFIED
llama3.2:3b       a80c4f17acd5    2.0 GB    5 minutes ago
```

## Docker

```bash
docker compose up -d
docker compose ps
docker logs ollama --tail=50
docker logs open-webui --tail=50
docker stats --no-stream
```

# Пример вывода docker compose ps:
```
NAME            IMAGE                                    COMMAND               SERVICE       CREATED       STATUS       PORTS
ollama          ollama/ollama                            "/bin/ollama serve"   ollama        2 min ago     Up 2 min     127.0.0.1:11434->11434/tcp
open-webui      ghcr.io/open-webui/open-webui:main      "bash start.sh"       open-webui    2 min ago     Up 2 min     127.0.0.1:3000->8080/tcp
```

## Проверка портов

```bash
ss -tlnp | grep -E '11434|3000|443'
sudo ufw status verbose
curl http://localhost:11434/api/tags
curl -I http://localhost:3000
```

# Пример безопасного вывода ss -tlnp:
```
LISTEN  0  4096  127.0.0.1:11434  0.0.0.0:*  users:(("ollama",pid=1234,fd=3))
LISTEN  0  4096  127.0.0.1:3000   0.0.0.0:*  users:(("docker-proxy",pid=5678,fd=4))
LISTEN  0  511   0.0.0.0:443      0.0.0.0:*  users:(("nginx",pid=9012,fd=8))
```

Порты 11434 и 3000 — только на 127.0.0.1. Порт 443 — открыт для интернета. Это правильно.

## API

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"Привет","stream":false}'
```

# Пример вывода:
```json
{
  "model": "llama3.2:3b",
  "response": "Привет! Чем могу помочь?",
  "done": true,
  "eval_count": 8,
  "total_duration": 2100000000
}
```

## Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

# Пример вывода nginx -t:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Ресурсы

```bash
free -h
df -h
nproc
nvidia-smi
```

## Диагностика при сбоях

```bash
# Логи systemd Ollama
journalctl -u ollama -n 20

# Ollama использует GPU?
docker logs ollama --tail=30 | grep -i "cuda\|gpu\|offload"

# Ollama слушает только локально?
ss -tlnp | grep 11434
```
