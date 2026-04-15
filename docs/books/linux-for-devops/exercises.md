# Упражнения к книге «Linux для DevOps»

---

## Глава 0: Подготовка окружения

### 0.1 Установка VirtualBox
- Установи VirtualBox на свою систему
- Открой его — убедись, что работает

### 0.2 Скачивание Ubuntu
- Скачай Ubuntu Server 24.04 LTS ISO
- Проверь что файл скачался

### 0.3 Создание VM
- Создай виртуальную машину (2 ГБ RAM, 25 ГБ диск)
- Подключи ISO

### 0.4 Установка Ubuntu
- Запусти VM → пройди установку
- Обязательно выбери SSH при установке
- Войди в систему

### 0.5 Первый снапшот
- `sudo poweroff` — выключи VM
- Создай снапшот «Clean Install» в VirtualBox

### 0.6 SSH-подключение
- Узнай IP виртуалки: `hostname -I`
- Подключись со своего компьютера: `ssh username@IP`
- Введи пароль — убедись что вход работает
- Выйди обратно: `exit`

---

## Глава 1: Что такое Linux

### 1.1 Установка Ubuntu Server
- Установи Ubuntu Server на виртуальную машину
- **Критерий:** Видишь приглашение командной строки

### 1.2 Вход в систему
- Войди под своим пользователем
- **Проверь:** `$` в конце приглашения (не `#`)

### 1.3 Проверка SSH
```bash
sudo systemctl status ssh
```
- **Проверь:** статус `active`

### 1.4 Кто я?
```bash
whoami
hostname
```
- Запомни оба значения

---

## Глава 2: Первая команда и файловая система

### 2.1 Навигация
- `pwd` → узнай где ты
- `cd /etc` → перейди в /etc
- `pwd` → проверь
- `cd` → вернись домой

### 2.2 Изучение системы
- `cd /` → корень
- `ls` → посмотри
- `cd /var/log` → логи
- `ls -la` → подробно

### 2.3 Пути
- Абсолютный: `cd /var/log`
- Относительный: от дома до `/var/log`

### 2.4 Специальные пути
- `cd ..` → наверх
- `cd -` → назад
- `cd ~` → домой

### 2.5 Автодополнение
- `cd /e<Tab>` → что произошло?
- `history` → сколько команд?

---

## Глава 3: Файлы и директории

### 3.1 Структура проекта
```bash
mkdir -p ~/myproject/{src,tests,docs,config}
touch ~/myproject/src/main.py
touch ~/myproject/tests/test_main.py
touch ~/myproject/docs/README.md
touch ~/myproject/config/settings.ini
```

### 3.2 Копирование
```bash
mkdir ~/backup
cp -r ~/myproject ~/backup/myproject
```

### 3.3 Чтение файлов
```bash
echo "Hello World" > ~/hello.txt
cat ~/hello.txt
tail /var/log/syslog
```

### 3.4 Поиск
```bash
find ~ -name "*.py"
find /var -type d
sudo find / -size +50M
```

### 3.5 Wildcard
```bash
touch file{1,2,3,4,5}.txt
ls *.txt
rm file{2,4}.txt
```

### 3.6 Перенаправление и pipe
```bash
echo "line 1" > test.txt
echo "line 2" >> test.txt
cat test.txt
ps aux | wc -l
history | grep "ls"
du -sh /var/* | sort -rh | head -5
```

### 3.7 DevOps Think
**«Найди все конфигурационные файлы Nginx»**
1. `find /etc/nginx -name "*.conf"`
2. `find ... | wc -l` — сколько?
3. `cat /etc/nginx/nginx.conf`

---

## Глава 4: Права и владельцы

### 4.1 Чтение прав
```bash
ls -l ~          # что у .bashrc?
ls -ld /tmp      # что значит t?
ls -l /etc/shadow # почему не читать?
```

### 4.2 Изменение прав
```bash
touch ~/script.sh
chmod +x ~/script.sh
ls -l ~/script.sh
chmod -x ~/script.sh
```

### 4.3 Цифровые права
```bash
touch ~/secret.txt
chmod 600 ~/secret.txt
chmod 644 ~/secret.txt
chmod 755 ~/secret.txt
```

### 4.4 Смена владельца
```bash
touch ~/owned.txt
sudo chown root ~/owned.txt
sudo chown $USER ~/owned.txt
```

### 4.5 Практика для DevOps
```bash
mkdir -p ~/webapp/{public,logs,config}
sudo chown -R www-data:www-data ~/webapp
sudo chmod 755 ~/webapp/public
sudo chmod 640 ~/webapp/config/settings.ini
```

---

## Глава 5: Редакторы

### 5.1 nano
- Создай файл, напиши 3 строки, сохрани, выйди

### 5.2 nano — редактирование
- Открой `~/.bashrc`, раскомментируй строку

### 5.3 vim — минимум
- `vim ~/test.txt` → `i` → писать → `Esc` → `:wq`

### 5.4 vim — навигация
- 10 строк → `gg`, `G`, `j`, `k`, `/`, `dd`, `:wq`

### 5.5 Конфиг приложения
- Создай `config.ini` с секциями server, database, logging

---

## Глава 6: Процессы

### 6.1 Посмотреть процессы
```bash
ps aux
ps aux | grep ssh
ps aux | head -2
```

### 6.2 Мониторинг
- `top` → `M` → `P` → `q`
- `htop` (если установлен)

### 6.3 Запустить и убить
```bash
sleep 300 &
jobs -l
kill <PID>
```

### 6.4 Фоновые задачи
```bash
python3 -c "import time; time.sleep(60)" &
jobs
fg %1
Ctrl+Z
bg
```

### 6.5 nohup
```bash
nohup sleep 600 &
# Закрыть терминал, открыть снова
ps aux | grep sleep
```

### 6.6 tmux — основы
```bash
sudo apt install -y tmux
tmux new -s test        # создать сессию
# Ctrl+b, d — отключиться
tmux ls                 # список сессий
tmux attach -t test     # подключиться
tmux kill-session -t test
```

### 6.7 tmux — панели
```bash
tmux new -s panels
# Ctrl+b " — разделить горизонтально
# Ctrl+b % — разделить вертикально
# Ctrl+b стрелка — переключение между панелями
# Запусти в разных панелях: tail -f, htop, df -h
# Отключись и подключись — всё на месте?
```

### 6.8 DevOps Think
**«Процесс nginx перестал отвечать. Найди и диагностируй»**
1. `ps aux | grep nginx` — работает ли?
2. `pgrep nginx` — PID?
3. `sudo journalctl -u nginx -n 50` — логи
4. `ss -tlnp | grep 80` — порт открыт?
5. `curl -I http://localhost` — отвечает ли?

---

## Глава 7: Системные сервисы

### 7.1 Изучить сервисы
```bash
systemctl list-units --type=service
systemctl status ssh
systemctl list-unit-files --state=enabled
```

### 7.2 Управление
```bash
systemctl status cron
sudo systemctl stop cron
sudo systemctl start cron
```

### 7.3 Создать сервис
- worker.py + myapp-worker.service

### 7.4 Автоперезапуск
- Убей процесс → подожди → проверь что перезапустился

---

## Глава 8: Логи

### 8.1 Изучить логи
```bash
tail /var/log/syslog
tail -n 50 /var/log/syslog
grep -i "error" /var/log/syslog
tail /var/log/auth.log
```

### 8.2 Следить
- `tail -f` в одном окне, `systemctl restart ssh` в другом

### 8.3 journalctl
```bash
sudo journalctl -u nginx
sudo journalctl --since today
sudo journalctl -p err
```

### 8.4 Диагностика
- `systemctl status nginx` → `journalctl -u nginx` → `nginx -t`

### 8.5 DevOps Think
**«Диск забит на 95%. Найди виновника за 5 минут»**
1. `df -h` — общая картина
2. `sudo du -sh /* | sort -rh | head -5` — большие директории
3. `sudo du -sh /var/* | sort -rh | head -5` — копай в /var
4. `sudo find /var -size +100M 2>/dev/null` — конкретные файлы
5. `sudo journalctl --vacuum-size=100M` — очисти логи

**«Сервис не стартует после перезагрузки. Диагностируй»**
1. `systemctl is-enabled myapp` — включён ли автозапуск?
2. `systemctl status myapp` — статус
3. `sudo journalctl -u myapp --since today` — логи
4. Проверь зависимости в `.service` файле
5. `systemctl status <зависимость>` — запущены ли зависимости?

---

## Глава 9: Пользователи

### 9.1 Создать deploy
```bash
sudo useradd -m -s /bin/bash -c "Deploy User" deploy
sudo passwd deploy
id deploy
```

### 9.2 Группы
```bash
sudo groupadd devteam
sudo usermod -aG devteam $USER
sudo gpasswd -d deploy devteam
```

### 9.3 SSH-ключи и подключение
```bash
# Генерация
ssh-keygen -t ed25519 -C "your@email"
# задай passphrase когда спросит

# Копирование на сервер
ssh-copy-id username@server-ip

# Проверка — пароль сервера больше не спрашивается?
ssh username@server-ip

# Алиас
nano ~/.ssh/config
# Host devops
#     HostName 192.168.1.100
#     User username
#     IdentityFile ~/.ssh/id_ed25519
ssh devops
```

### 9.4 su и sudo
```bash
sudo su - deploy
whoami
pwd
exit
```

### 9.5 Безопасность
```bash
cat /etc/passwd
grep "/bin/bash" /etc/passwd
grep sudo /etc/group
```

---

## Глава 10: Сеть

### 10.1 Своя сеть
```bash
hostname -I
ip addr
```

### 10.2 Порты
```bash
ss -tlnp
nc -zv localhost 22
```

### 10.3 curl
```bash
curl -I https://google.com
curl -I http://localhost
```

### 10.4 ping
```bash
ping -c 4 google.com
```

### 10.5 Фаервол
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## Глава 11: Диски

### 11.1 Проверить диск
```bash
df -h
lsblk
free -h
```

### 11.2 Большие файлы
```bash
sudo du -sh /* | sort -rh | head -5
sudo find / -size +100M 2>/dev/null
```

### 11.3 Очистка
```bash
sudo apt clean
sudo apt autoremove
sudo journalctl --vacuum-size=100M
```

### 11.4 Swap
- Проверить, создать если нет, добавить в fstab

---

## Глава 12: Shell-скрипты

### 12.1 Первый скрипт
- `hello.sh` с датой и hostname

### 12.2 check-service.sh
- Принимает имя сервиса, проверяет его и запускает, если нужно

### 12.3 Цикл по сервисам
- Все `.service` файлы → статус → подсчёт активных

### 12.4 backup.sh
- Бэкап конфигов → tar.gz → удалить старые > 7 дней → лог

---

## Глава 13: Пакетные менеджеры

### 13.1 Обновление
```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove
```

### 13.2 Установка
```bash
sudo apt install -y htop git
htop --version
git --version
```

### 13.3 Поиск
```bash
apt search python3 | head -20
apt show nginx
apt list --installed | head -20
```

### 13.4 Установка/удаление
```bash
sudo apt install -y sl
sl
sudo apt remove sl
sudo apt autoremove
```

---

## Глава 14: Итоговый проект

### Полное развёртывание
1. Подготовка сервера
2. Создание приложения (Flask)
3. Виртуальное окружение
4. Пользователь для приложения
5. systemd сервис
6. Nginx reverse proxy
7. Скрипт деплоя
8. Проверка всего
9. Перезагрузка → проверка

### Финальный чеклист
- [ ] `curl http://localhost` работает
- [ ] `systemctl status myapp` active
- [ ] `systemctl status nginx` active
- [ ] Логи пишутся
- [ ] После перезагрузки всё работает
- [ ] Фаервол включён
- [ ] Могу объяснить каждую команду

---

*Все упражнения из книги «Linux для DevOps»*
