# Приложение A: Минимальный baseline

## SSH

```text
PasswordAuthentication no
PermitRootLogin no
ClientAliveInterval 300
ClientAliveCountMax 2
```

Проверка:

```bash
sudo sshd -t
```

# Пример вывода (успех):
```
(нет вывода — файл без ошибок)
```

```bash
sudo systemctl restart ssh
ssh user@server
```

## Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status verbose
```

# Пример вывода `ufw status verbose`:
```
Status: active
Default: deny (incoming), allow (outgoing), disabled (routed)

To                         Action      From
--                         ------      ----
22/tcp                     LIMIT IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
```

## Updates

```bash
sudo apt install unattended-upgrades
sudo unattended-upgrade --dry-run -v
```

# Пример вывода:
```
Packages that will be upgraded: libssl1.1 openssh-server
This is a dry run, no changes will be applied.
```

## fail2ban

```bash
sudo apt install fail2ban
sudo fail2ban-client status sshd
```

# Пример вывода:
```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 3
|  `- Total failed:     247
`- Actions
   |- Currently banned: 2
   `- Banned IP list:   45.33.32.156 185.234.218.5
```
