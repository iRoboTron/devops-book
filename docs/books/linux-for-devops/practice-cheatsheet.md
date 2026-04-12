# Шпаргалка к тренировочному списку — Книга 1: Linux для DevOps

> Здесь те же задания что в [practice-drill.md](practice-drill.md), но с командами.
> Используй как подсказку — сначала попробуй без шпаргалки.

---

## Блок 1: Подключение и ориентация

**1. Подключись по SSH к серверу**
```bash
ssh username@192.168.1.100
```

**2. Узнай в какой директории находишься**
```bash
pwd
```

**3. Содержимое текущей директории**
```bash
ls
```

**4. Подробный список (права, владелец, размер, дата)**
```bash
ls -l
```

**5. Список включая скрытые файлы**
```bash
ls -la
```

**6. Перейди в корень файловой системы**
```bash
cd /
```

**7. Посмотри что там есть**
```bash
ls
```

**8. Вернись в домашнюю директорию**
```bash
cd ~
# или просто:
cd
```

**9. Имя текущего пользователя**
```bash
whoami
```

**10. Имя хоста**
```bash
hostname
```

---

## Блок 2: Файлы и директории

**11. Создать директорию `~/devops-practice`**
```bash
mkdir ~/devops-practice
```

**12. Перейти в неё**
```bash
cd ~/devops-practice
```

**13. Создать три поддиректории**
```bash
mkdir app logs config
```

**14. Создать пустой файл `app/main.py`**
```bash
touch app/main.py
```

**15. Создать пустой файл `config/settings.conf`**
```bash
touch config/settings.conf
```

**16. Записать строку в файл**
```bash
echo "PORT=8000" > config/settings.conf
```

**17. Добавить строку не затирая (append)**
```bash
echo "DEBUG=true" >> config/settings.conf
```

**18. Вывести содержимое файла**
```bash
cat config/settings.conf
```

**19. Скопировать файл**
```bash
cp config/settings.conf config/settings.conf.bak
```

**20. Переименовать файл**
```bash
mv config/settings.conf.bak config/settings.backup
```

**21. Только первая строка файла**
```bash
head -1 config/settings.conf
```

**22. Только последняя строка файла**
```bash
tail -1 config/settings.conf
```

**23. Найти все `.py` файлы**
```bash
find ~/devops-practice -name "*.py"
```

**24. Найти все `.conf` файлы**
```bash
find ~/devops-practice -name "*.conf"
```

**25. Дерево директорий (рекурсивный ls)**
```bash
ls -R ~/devops-practice
# или если установлен tree:
tree ~/devops-practice
```

---

## Блок 3: Права и владельцы

**26. Посмотреть права файла**
```bash
ls -l app/main.py
```

**27. Права 755 (rwxr--r--) для владельца+выполнение, остальные только чтение**
```bash
chmod 744 app/main.py
# или буквенно:
chmod u=rwx,go=r app/main.py
```

**28. Права 600 (rw-------) — только владелец**
```bash
chmod 600 config/settings.conf
```

**29. Записать строку в main.py**
```bash
echo '#!/usr/bin/env python3' > app/main.py
echo 'print("Hello from DevOps practice!")' >> app/main.py
```

**30. Запустить файл как исполняемый**
```bash
./app/main.py
# или:
python3 app/main.py
```

**31. От чьего имени выполняются команды**
```bash
whoami
id
```

**32. Выполнить whoami от имени root**
```bash
sudo whoami
```

**33. Текущая umask**
```bash
umask
```

---

## Блок 4: Пользователи и SSH

**34. Создать пользователя `devops`**
```bash
sudo useradd -m -s /bin/bash devops
```

**35. Задать пароль**
```bash
sudo passwd devops
```

**36. Добавить в группу `sudo`**
```bash
sudo usermod -aG sudo devops
```

**37. Проверить группы пользователя**
```bash
groups devops
# или:
id devops
```

**38. Создать директорию `~/.ssh`**
```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

**39. Сгенерировать SSH-ключ**
```bash
ssh-keygen -t ed25519 -C "devops-practice" -f ~/.ssh/id_devops_practice
# когда спросит — задай passphrase
```

**40. Посмотреть публичный ключ**
```bash
cat ~/.ssh/id_devops_practice.pub
```

**41. Добавить публичный ключ в authorized_keys пользователя devops**
```bash
sudo mkdir -p /home/devops/.ssh
cat ~/.ssh/id_devops_practice.pub | sudo tee /home/devops/.ssh/authorized_keys
```

**42. Установить правильные права**
```bash
sudo chmod 700 /home/devops/.ssh
sudo chmod 600 /home/devops/.ssh/authorized_keys
sudo chown -R devops:devops /home/devops/.ssh
```

**43. Список всех пользователей (первые 10)**
```bash
head -10 /etc/passwd
```

**44. Заблокировать пользователя**
```bash
sudo usermod -L devops
```

**45. Разблокировать пользователя**
```bash
sudo usermod -U devops
```

---

## Блок 5: Процессы

**46. Список всех запущенных процессов**
```bash
ps aux
```

**47. Интерактивный мониторинг**
```bash
top
# или (лучше):
htop
# выход: q
```

**48. Запустить `sleep 300` в фоне**
```bash
sleep 300 &
```

**49. Список фоновых задач**
```bash
jobs
```

**50. Найти PID процесса `sleep`**
```bash
pgrep sleep
# или:
ps aux | grep sleep
```

**51. Завершить процесс мягко (SIGTERM)**
```bash
kill <PID>
```

**52. Убить принудительно (SIGKILL)**
```bash
sleep 400 &
kill -9 $(pgrep "sleep 400")
# или:
kill -KILL <PID>
```

**53. Использование памяти**
```bash
free -h
```

**54. Статистика CPU (одна строка)**
```bash
top -bn1 | grep "Cpu(s)"
# или:
vmstat 1 1
```

**55. Найти все процессы с именем bash**
```bash
pgrep -l bash
# или:
ps aux | grep bash
```

---

## Блок 6: Системные сервисы

**56. Создать файл юнита**
```bash
sudo nano /etc/systemd/system/practice-app.service
```
Содержимое файла:
```ini
[Unit]
Description=Practice App
After=network.target

[Service]
Type=simple
ExecStart=/bin/sleep 9999
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**57. Перезагрузить конфигурацию systemd**
```bash
sudo systemctl daemon-reload
```

**58. Запустить сервис**
```bash
sudo systemctl start practice-app
```

**59. Проверить статус**
```bash
sudo systemctl status practice-app
```

**60. Включить в автозапуск**
```bash
sudo systemctl enable practice-app
```

**61. Посмотреть логи сервиса**
```bash
journalctl -u practice-app -n 20
```

**62. Остановить сервис**
```bash
sudo systemctl stop practice-app
```

**63. Убедиться что остановлен**
```bash
sudo systemctl status practice-app
# Должен показать: inactive (dead)
```

**64. Отключить автозапуск**
```bash
sudo systemctl disable practice-app
```

---

## Блок 7: Логи и диагностика

**65. Последние 20 строк системного лога**
```bash
tail -20 /var/log/syslog
# или на systemd-системах:
journalctl -n 20
```

**66. Следить за логом в реальном времени**
```bash
tail -f /var/log/syslog
# Ctrl+C для выхода
```

**67. Найти строки с "error" без учёта регистра**
```bash
grep -i "error" /var/log/syslog
```

**68. Логи systemd за последние 10 минут**
```bash
journalctl --since "10 minutes ago"
```

**69. Логи только для сервиса ssh**
```bash
journalctl -u ssh
# или:
journalctl -u sshd
```

**70. Записать строку с датой в файл**
```bash
echo "[$(date)] Test log entry" >> ~/devops-practice/logs/test.log
```

**71. Следить за файлом логов**
```bash
tail -f ~/devops-practice/logs/test.log
```

**72. Добавить строки в файл (в другой вкладке)**
```bash
echo "[$(date)] Second entry" >> ~/devops-practice/logs/test.log
echo "[$(date)] Third entry" >> ~/devops-practice/logs/test.log
```

**73. Найти строки за сегодня**
```bash
grep "$(date '+%a %b')" ~/devops-practice/logs/test.log
# или по дате в формате который ты использовал
```

**74. Посчитать количество строк**
```bash
wc -l ~/devops-practice/logs/test.log
```

---

## Блок 8: Сеть

**75. Все сетевые интерфейсы и IP**
```bash
ip addr
# или короче:
ip a
```

**76. Какие порты слушают (TCP + процессы)**
```bash
ss -tlnp
# или:
sudo ss -tlnp
```

**77. Пинг google.com (3 пакета)**
```bash
ping -c 3 google.com
```

**78. Только заголовки ответа (без тела)**
```bash
curl -I http://example.com
```

**79. Скачать содержимое в файл**
```bash
curl -o ~/devops-practice/example.html http://example.com
```

**80. Первые 5 строк файла**
```bash
head -5 ~/devops-practice/example.html
```

**81. Статус файрвола**
```bash
sudo ufw status
```

**82. DNS-серверы**
```bash
cat /etc/resolv.conf
```

**83. Внешний IP-адрес**
```bash
curl ifconfig.me
# или:
curl icanhazip.com
```

**84. Проверить доступность порта 80 на localhost**
```bash
nc -zv localhost 80
# или:
curl -s -o /dev/null -w "%{http_code}" http://localhost
```

---

## Блок 9: Диски

**85. Место на всех дисках**
```bash
df -h
```

**86. Размер директории `~/devops-practice`**
```bash
du -sh ~/devops-practice
```

**87. Размер каждой поддиректории**
```bash
du -sh ~/devops-practice/*
```

**88. 5 самых больших файлов в `/var`**
```bash
sudo find /var -type f -printf "%s %p\n" 2>/dev/null | sort -rn | head -5
```

**89. Список блочных устройств**
```bash
lsblk
```

**90. Смонтированные файловые системы**
```bash
mount | grep -v "tmpfs\|cgroup"
# или:
df -hT
```

---

## Блок 10: Пакеты

**91. Обновить список пакетов**
```bash
sudo apt update
```

**92. Найти пакет htop**
```bash
apt search htop
```

**93. Установить htop**
```bash
sudo apt install -y htop
```

**94. Информация о пакете**
```bash
apt show htop
```

**95. Установить tree**
```bash
sudo apt install -y tree
```

**96. Посмотреть дерево директорий**
```bash
tree ~/devops-practice
```

**97. Проверить доступные обновления**
```bash
apt list --upgradable 2>/dev/null
```

**98. Удалить tree**
```bash
sudo apt remove -y tree
```

---

## Блок 11: Shell-скрипт

**99–101. Создать и написать скрипт**
```bash
cat > ~/devops-practice/app/check.sh << 'EOF'
#!/bin/bash
set -e

echo "=== System Check ==="
echo "Date:  $(date)"
echo "User:  $(whoami)"

FREE_GB=$(df -BG / | awk 'NR==2 {gsub("G",""); print $4}')
echo "Free disk space on /: ${FREE_GB}G"

if [ "$FREE_GB" -lt 1 ]; then
    echo "WARNING: low disk space"
else
    echo "OK: disk space is fine"
fi
EOF

chmod +x ~/devops-practice/app/check.sh
```

**102. Запустить скрипт**
```bash
~/devops-practice/app/check.sh
```

**103. Передать через grep**
```bash
~/devops-practice/app/check.sh | grep "Date"
```

---

## Блок 12: Pipe и фильтры

**104. Файлы в /etc содержащие "nginx" в имени**
```bash
ls /etc | grep nginx
```

**105. 10 самых нагруженных процессов по CPU**
```bash
ps aux --sort=-%cpu | head -11
```

**106. Сколько файлов в /etc**
```bash
ls /etc | wc -l
```

**107. Уникальные расширения файлов в /etc**
```bash
find /etc -maxdepth 1 -type f | sed 's/.*\.//' | sort | uniq
```

**108. Файлы в /var/log больше 1MB**
```bash
sudo find /var/log -type f -size +1M -ls
```

---

## Финальная уборка

**109. Остановить и удалить сервис `practice-app`**
```bash
sudo systemctl stop practice-app
sudo systemctl disable practice-app
sudo rm /etc/systemd/system/practice-app.service
sudo systemctl daemon-reload
```

**110. Удалить пользователя `devops`**
```bash
sudo userdel -r devops
```

**111. Удалить всё что создали — одна команда**
```bash
rm -rf ~/devops-practice
```

**112. Проверить что папка удалилась**
```bash
ls ~/devops-practice
# Должно показать: No such file or directory
```

---

> Всё удалено. Можно начать с чистого листа в любой момент.
> Просто снова открой [practice-drill.md](practice-drill.md) и начни с задания 11.

---

## Быстрая шпаргалка по командам (справочник)

| Задача | Команда |
|--------|---------|
| Где я? | `pwd` |
| Список файлов | `ls -la` |
| Перейти в папку | `cd путь` |
| Домой | `cd ~` или `cd` |
| Создать папку | `mkdir имя` |
| Создать файл | `touch имя` |
| Записать в файл | `echo "текст" > файл` |
| Добавить в файл | `echo "текст" >> файл` |
| Прочитать файл | `cat файл` |
| Копировать | `cp источник куда` |
| Переместить/переименовать | `mv источник куда` |
| Удалить файл | `rm файл` |
| Удалить папку | `rm -rf папка` |
| Права файла | `chmod 755 файл` |
| Владелец файла | `chown user:group файл` |
| Создать пользователя | `sudo useradd -m -s /bin/bash имя` |
| Добавить в группу | `sudo usermod -aG группа пользователь` |
| Список процессов | `ps aux` |
| Убить процесс | `kill PID` |
| Убить принудительно | `kill -9 PID` |
| Запустить в фоне | `команда &` |
| Статус сервиса | `systemctl status имя` |
| Запустить сервис | `sudo systemctl start имя` |
| Остановить сервис | `sudo systemctl stop имя` |
| Автозапуск вкл | `sudo systemctl enable имя` |
| Логи сервиса | `journalctl -u имя -n 50` |
| Место на диске | `df -h` |
| Размер папки | `du -sh папка` |
| Сетевые интерфейсы | `ip addr` |
| Открытые порты | `ss -tlnp` |
| Установить пакет | `sudo apt install -y имя` |
| Удалить пакет | `sudo apt remove -y имя` |
| Найти в файле | `grep "текст" файл` |
| Найти файлы | `find путь -name "*.ext"` |
| SSH-ключ | `ssh-keygen -t ed25519 -f ~/.ssh/имя` |
