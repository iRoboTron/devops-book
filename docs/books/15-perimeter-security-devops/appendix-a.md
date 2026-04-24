# Приложение A: Шпаргалка команд

---

## Аудит открытых портов и сервисов

```bash
ss -tulpn
sudo lsof -i -P -n | grep LISTEN
systemctl list-units --type=service --state=running
```

---

## Firewall

```bash
sudo ufw status verbose
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## SSH

```bash
sudo sshd -t
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries|logingracetime'
sudo systemctl reload ssh
sudo journalctl -u ssh -n 50 --no-pager
```

---

## Fail2ban

```bash
sudo systemctl status fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo journalctl -u fail2ban -n 50 --no-pager
```

---

## Проверки со своей второй машины

```bash
nmap -Pn SERVER_IP
nmap -Pn -p 22,80,443,5432,3306,6379 SERVER_IP
curl -I http://HOST
curl -Ik https://HOST
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no user@HOST
```
