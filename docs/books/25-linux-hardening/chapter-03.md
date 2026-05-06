# Глава 3: Firewall и открытые порты

> **Цель:** наружу открыто только то, что действительно нужно.

---

## 3.1 Посмотреть реальность

```bash
sudo ss -tlnp
```

# Пример вывода:
```
State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      128    0.0.0.0:22          0.0.0.0:*         users:(("sshd",pid=812,fd=3))
LISTEN 0      128    0.0.0.0:80          0.0.0.0:*         users:(("nginx",pid=1024,fd=6))
LISTEN 0      128    127.0.0.1:5432      0.0.0.0:*         users:(("postgres",pid=1234,fd=5))
LISTEN 0      511    0.0.0.0:443         0.0.0.0:*         users:(("nginx",pid=1024,fd=7))
LISTEN 0      128    0.0.0.0:8080        0.0.0.0:*         users:(("docker-proxy",pid=2001,fd=4))
```

Обрати внимание: `127.0.0.1:5432` — postgres слушает только локально (правильно). `0.0.0.0:8080` — docker-proxy слушает на всех интерфейсах (возможно, не нужно).

```bash
sudo ufw status verbose
```

# Пример вывода:
```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     LIMIT IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
51820/udp                  ALLOW IN    Anywhere
22/tcp (v6)                LIMIT IN    Anywhere (v6)
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)
51820/udp (v6)             ALLOW IN    Anywhere (v6)
```

`Default: deny (incoming)` — всё входящее запрещено кроме явно указанного. Это правильная базовая политика.

```bash
sudo ufw status numbered
```

---

## 3.2 Default deny

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp
```

# Пример вывода:
```
Rules updated
Rules updated (v6)
```

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 51820/udp
```

Не включай firewall, пока не уверен, что SSH разрешён.

---

## 3.3 Сервисы только через VPN

```bash
sudo ufw allow from 10.0.0.0/24 to any port 3000 proto tcp
sudo ufw deny 3000/tcp
```

> **Аналогия:** Firewall — это фейс-контроль на входе. ufw — список тех, кого пускают. Но Docker умеет обходить фейс-контроль через служебный вход (iptables). Поэтому нужно проверять оба места.

Лучше ещё сильнее: настроить сервис слушать `127.0.0.1` или `10.0.0.1`, а не `0.0.0.0`.

---

## 3.4 Проблема Docker и ufw

Docker добавляет собственные правила в iptables напрямую, минуя ufw. Это значит: даже если в ufw порт закрыт — Docker может открыть его наружу через цепочку DOCKER в таблице nat.

Проверить что Docker реально пробросил:

```bash
sudo iptables -t nat -L DOCKER --line-numbers
```

# Пример вывода:
```
Chain DOCKER (2 references)
num  target     prot opt source               destination
1    RETURN     all  --  anywhere             anywhere
2    DNAT       tcp  --  anywhere             anywhere             tcp dpt:8080 to:172.17.0.2:8080
3    DNAT       tcp  --  anywhere             anywhere             tcp dpt:3000 to:172.17.0.3:3000
```

Строки DNAT означают: Docker пробросил эти порты наружу. Даже если в ufw для них нет правила ALLOW.

Решение: в `compose.yml` привязывай порт к `127.0.0.1`:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

Тогда Docker создаёт DNAT только на localhost, и снаружи порт недоступен.

---

## 3.5 Если что-то пошло не так

> **Если что-то пошло не так:**
>
> **Симптом:** После включения ufw SSH перестал работать, соединение потеряно.
>
> **Шаги исправления:**
> 1. Если старый сеанс жив — сразу выполни: `sudo ufw allow 22/tcp`
> 2. Если доступа нет — используй консоль провайдера.
> 3. В консоли: `sudo ufw disable` — временно выключит firewall.
> 4. Добавь правило для SSH: `sudo ufw allow 22/tcp`
> 5. Включи снова: `sudo ufw enable`
>
> **Симптом:** Docker-контейнер не принимает соединения после настройки ufw.
>
> Проверь, не закрыл ли ты порт, который Docker всё равно публикует через iptables. Смотри раздел 3.4.

---

## 3.6 Практика

Сравни ожидаемые и реальные порты:

| Порт | Сервис | Должен быть открыт? | Откуда доступен? |
|---|---|---|---|

Практика завершена, если каждый открытый порт имеет понятную причину.
