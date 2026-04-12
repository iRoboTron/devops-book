# Глава 3: Nginx — первые шаги

> **Запомни:** Nginx — это привратник. Всё что приходит из интернета — сначала попадает в Nginx. Научись им управлять — управляешь всем сервером.

---

## 3.1 Что такое веб-сервер и зачем он нужен

Твоё Python-приложение **может** слушать порт и отвечать на HTTP-запросы.
Но оно не умеет:

- Обрабатывать 10 000 одновременных соединений
- Отдавать статические файлы (CSS, JS, картинки) быстро
- Кэшировать ответы
- Сжимать данные (gzip)
- Балансировать нагрузку между серверами
- Работать с SSL-сертификатами эффективно

**Nginx** умеет всё это.

```
Браузер ───→ Nginx (привратник, 10к соединений) ───→ Python (логика, 100 соединений)
```

### Почему не напрямую к Python?

```
Прямое подключение:
Браузер ───→ Python
  ❌ Python тратит ресурсы на SSL, статику, кеши
  ❌ Python блокируется на медленных клиентах
  ❌ Один сервер = одна точка отказа

Через Nginx:
Браузер ───→ Nginx ───→ Python
  ✅ Nginx берёт на себя всю рутину
  ✅ Python занимается только логикой
  ✅ Nginx может кешировать и раздавать статику
  ✅ Можно добавить второй Python-сервер
```

> **Запомни:** Python — для бизнес-логики.
> Nginx — для всего остального.

---

## 3.2 Установка и запуск Nginx

### Установка

```bash
sudo apt update
sudo apt install -y nginx
```

### Проверить что установлен

```bash
nginx -v
nginx version: nginx/1.24.0 (Ubuntu)
```

### Запустить

```bash
sudo systemctl enable --now nginx
```

`enable` — автозапуск при старте.
`--now` — запустить сейчас.

### Проверить статус

```bash
systemctl status nginx
● nginx.service - A high performance web server
     Active: active (running)
```

### Проверить что работает

Открой браузер и введи IP сервера:

```
http://192.168.1.100
```

Или с того же сервера:

```bash
curl -I http://localhost
HTTP/1.1 200 OK
Server: nginx/1.24.0 (Ubuntu)
```

Увидел **200 OK** и `Server: nginx` — работает!

---

## 3.3 Структура конфигурации Nginx

Nginx хранит конфиги в `/etc/nginx/`.

```
/etc/nginx/
├── nginx.conf                    ← главный файл
├── sites-available/              ← конфиги сайтов (все)
│   └── default                   ← дефолтный сайт
├── sites-enabled/                ← включённые сайты (symlinks)
│   └── default → ../sites-available/default
├── conf.d/                       ← дополнительные конфиги
├── modules-available/            ← доступные модули
├── modules-enabled/              ← включённые модули
├── mime.types                    ← типы файлов
└── fastcgi.conf                  ← для PHP
```

### Главный файл: `nginx.conf`

```bash
cat /etc/nginx/nginx.conf
```

Внутри три уровня блоков:

```nginx
# Глобальные настройки (сколько рабочих процессов и т.д.)
user www-data;
worker_processes auto;

http {
    # Настройки для всех сайтов
    sendfile on;
    keepalive_timeout 65;

    server {
        # Конфиг конкретного сайта
        listen 80;
        server_name myapp.ru;
        root /var/www/myapp;
    }

    server {
        # Ещё один сайт
        listen 80;
        server_name another.ru;
        root /var/www/another;
    }
}
```

### Иерархия

```
nginx.conf (глобально)
  └── http {} (все сайты)
        └── server {} (один сайт)
              └── location {} (один путь на сайте)
```

> **Запомни:** `nginx.conf` обычно не трогаешь.
> Все свои конфиги кладёшь в `sites-available/`.

---

## 3.4 sites-available vs sites-enabled

**sites-available** — все конфиги которые есть.
**sites-enabled** — только активные сайты (symlinks).

```
sites-available/
├── myapp.conf       ← есть, но не активен
└── default          ← есть и активен

sites-enabled/
└── default → ../sites-available/default  ← только symlink
```

### Включить сайт

```bash
sudo ln -s /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/
```

### Отключить сайт

```bash
sudo rm /etc/nginx/sites-enabled/myapp.conf
```

> **Совет:** Это позволяет иметь "заготовку" сайта
> и включать/выключать его без удаления конфига.

---

## 3.5 Минимальный конфиг для статического сайта

Создадим простую HTML-страницу и покажем её через Nginx.

### Шаг 1: Создай HTML

```bash
sudo mkdir -p /var/www/myapp
sudo nano /var/www/myapp/index.html
```

```html
<!DOCTYPE html>
<html>
<head><title>My App</title></head>
<body>
    <h1>Hello from Nginx!</h1>
    <p>Это статический сайт.</p>
</body>
</html>
```

### Шаг 2: Создай конфиг

```bash
sudo nano /etc/nginx/sites-available/myapp.conf
```

```nginx
server {
    listen 80;
    server_name myapp.local;

    root /var/www/myapp;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

### Разбор каждой строки

```nginx
server {
```
Начало конфига одного сайта.

```nginx
    listen 80;
```
Слушать порт 80 (HTTP).

```nginx
    server_name myapp.local;
```
Отвечать только на запросы для `myapp.local`.
Если запрос для другого домена — Nginx проигнорирует этот блок.

```nginx
    root /var/www/myapp;
```
Где лежат файлы сайта.
Когда браузер просит `/index.html` — Nginx ищет `/var/www/myapp/index.html`.

```nginx
    index index.html;
```
Если просят директорию (`/`) — отдать `index.html`.

```nginx
    location / {
        try_files $uri $uri/ =404;
    }
```
`location /` — для всех запросов начиная с `/`.
`try_files` — попробуй:
1. Файл по URI (`$uri`)
2. Директорию по URI (`$uri/`)
3. Если ничего нет — верни 404

```nginx
}
```
Конец конфига.

> **Запомни:** Каждая строка заканчивается `;`.
> Забыл `;` — Nginx не запустится.

---

## 3.6 `nginx -t` — проверка конфига

> **Порядок важен:**
> **Всегда** запускай `nginx -t` **перед** reload/restart.
> Один забытый `;` может уронить **все** сайты на сервере.

```bash
sudo nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Если ошибка — покажет где:

```bash
sudo nginx -t
nginx: [emerg] unexpected end of file in /etc/nginx/sites-available/myapp.conf:12
nginx: configuration file /etc/nginx/nginx.conf test failed
```

Строка 12, файл `myapp.conf`.

> **Запомни:** `nginx -t` — это not optional.
> Это как `python -m py_compile` — проверяешь перед запуском.
> Выработай привычку.

---

## 3.7 Включение сайта и перезагрузка

### Включи сайт

```bash
sudo ln -s /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/
```

### Проверь конфиг

```bash
sudo nginx -t
```

### Перезагрузи Nginx

```bash
sudo systemctl reload nginx
```

### `reload` vs `restart`

| Команда | Что делает | Когда использовать |
|---------|-----------|-------------------|
| `reload` | Перечитывает конфиг, **не останавливая** сервер | Изменил конфиг сайта |
| `restart` | Останавливает и запускает заново | Обновил Nginx, изменил глобальные настройки |

> **Правило:** Почти всегда `reload`.
> `restart` нужен редко — он создаёт микро-паузу когда сервер не отвечает.

### Проверь что работает

```bash
curl http://myapp.local
```

Если добавил `myapp.local` в `/etc/hosts`:

```bash
echo "127.0.0.1 myapp.local" | sudo tee -a /etc/hosts
curl http://myapp.local
```

Должен вернуть HTML твоей страницы.

---

## 3.8 Логи Nginx

Nginx пишет два типа логов:

| Лог | Путь | Что пишет |
|-----|------|-----------|
| access | `/var/log/nginx/access.log` | Каждый запрос |
| error | `/var/log/nginx/error.log` | Ошибки и проблемы |

### access.log

```bash
tail /var/log/nginx/access.log
127.0.0.1 - - [09/Apr/2026:14:30:00 +0000] "GET / HTTP/1.1" 200 234 "-" "curl/8.5.0"
```

| Часть | Значение |
|-------|----------|
| `127.0.0.1` | IP клиента |
| `GET / HTTP/1.1` | Запрос |
| `200` | Статус-код |
| `234` | Размер ответа (байты) |
| `curl/8.5.0` | User-Agent (кто запросил) |

### error.log

```bash
tail /var/log/nginx/error.log
2026/04/09 14:30:00 [error] 1234#0: *5 open() "/var/www/myapp/notfound.html" failed (2: No such file or directory)
```

> **Совет:** Когда сайт не работает — смотри error.log первым делом.
> Там почти всегда причина.

### Следить за логами в реальном времени

```bash
sudo tail -f /var/log/nginx/access.log
```

Открой сайт в браузере — увидишь запросы в терминале.

---

## 📝 Упражнения

### Упражнение 3.1: Установка и первый запуск
**Задача:**
1. Установи Nginx: `sudo apt install -y nginx`
2. Проверь версию: `nginx -v`
3. Запусти: `sudo systemctl enable --now nginx`
4. Проверь статус: `systemctl status nginx`
5. Проверь ответ: `curl -I http://localhost`

### Упражнение 3.2: Статический сайт
**Задача:**
1. Создай `/var/www/myapp/index.html` с простым HTML
2. Создай конфиг в `/etc/nginx/sites-available/myapp.conf`
3. Создай symlink в `sites-enabled/`
4. Проверь конфиг: `sudo nginx -t`
5. Перезагрузи: `sudo systemctl reload nginx`
6. Добавь `myapp.local` в `/etc/hosts`
7. Проверь: `curl http://myapp.local`

### Упражнение 3.3: Сломать и починить
**Задача:** Намеренно сломай конфиг и почини по логу ошибки.
1. Открой конфиг: `sudo nano /etc/nginx/sites-available/myapp.conf`
2. Убери `;` после `listen 80`
3. Попробуй проверить: `sudo nginx -t` — что говорит?
4. Посмотри сообщение об ошибке — понимаешь где проблема?
5. Почини `;` — проверь снова: `sudo nginx -t`
6. Перезагрузи: `sudo systemctl reload nginx`

### Упражнение 3.4: Логи в реальном времени
**Задача:**
1. Открой два терминала (или tmux панели)
2. В первом: `sudo tail -f /var/log/nginx/access.log`
3. Во втором: `curl http://myapp.local` несколько раз
4. Видишь запросы в первом терминале?
5. Попробуй `curl http://myapp.local/notfound` — что в error.log?

### Упражнение 3.5: DevOps Think
**Задача:** «Все сайты на сервере перестали работать. Диагностируй»

Подсказки:
1. Запущен ли Nginx? `systemctl status nginx`
2. Если упал — почему? `sudo journalctl -u nginx -n 50`
3. Конфиг валидный? `sudo nginx -t`
4. Если конфиг сломан — что именно? `sudo nginx -t` покажет строку
5. Посмотри error.log: `tail /var/log/nginx/error.log`
6. Никто не менял конфиг? `ls -lt /etc/nginx/sites-enabled/` — свежий файл?

---

## 📋 Чеклист главы 3

- [ ] Я понимаю зачем нужен Nginx (не просто "веб-сервер" а зачем)
- [ ] Я могу установить и запустить Nginx
- [ ] Я понимаю структуру конфигов (`nginx.conf` → `http` → `server` → `location`)
- [ ] Я понимаю разницу `sites-available` vs `sites-enabled`
- [ ] Я могу создать минимальный конфиг для статического сайта
- [ ] Я **всегда** запускаю `nginx -t` перед reload
- [ ] Я понимаю разницу между `reload` и `restart`
- [ ] Я могу включить/отключить сайт через symlink
- [ ] Я знаю где логи и как их читать
- [ ] Я могу диагностировать проблему по error.log

**Всё отметил?** Переходи к Главе 4 — Nginx как обратный прокси.
