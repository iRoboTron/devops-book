# Глава 8: Практика безопасной проверки

> **Запомни:** в web security важна не демонстрация "как взломать", а проверка, что твои trust boundaries действительно держат входящий ввод и браузерное поведение.

---

## 8.1 Что мы проверяем

В этой главе ты не строишь offensive toolbox. Ты делаешь controlled validation своего приложения.

Проверки должны отвечать на вопросы:

- где приложение принимает недоверенный ввод;
- как оно экранирует вывод;
- как ведут себя сессии и cookie;
- не доверяет ли backend внешним URL и файлам слишком широко;
- что видно в логах и браузерных инструментах.

---

## 8.2 Безопасный набор инструментов

### DevTools браузера

Проверь:
- cookie flags;
- `Set-Cookie`;
- CORS headers;
- redirect chain;
- CSP и другие security headers.

### `curl`

Полезно для проверки:

```bash
curl -I https://HOST
curl -vk https://HOST/login
curl -H 'Origin: https://evil.example' -I https://HOST/api
```

### Логи приложения и reverse proxy

Нужно видеть:
- 4xx/5xx;
- подозрительные URI;
- burst к `/login`, `/reset`, `/upload`;
- ошибки в обработке внешних URL и файлов.

---

## 8.3 Controlled checks

### Проверка cookie и session policy

Смотри:
- есть ли `HttpOnly`;
- есть ли `Secure`;
- как ведёт себя `SameSite`;
- не слишком ли длинный срок жизни сессии.

```bash
curl -sI https://HOST/login -X POST \
  -d 'username=test&password=test' | grep -i set-cookie
```

Хороший результат:

```
set-cookie: session=xyz; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=1800
```

Для каждой auth-cookie нужно проверить: есть ли `HttpOnly`, `Secure`, адекватный `SameSite` и разумный TTL.

### Проверка XSS-защиты

Не делай вредных payload chains. Достаточно в своей lab проверить, что недоверенный ввод:
- не попадает в DOM как исполняемый HTML/JS;
- корректно отображается как текст;
- CSP не сломана и не бессмысленна.

### Проверка SSRF/file upload boundary

В своей lab:
- используй контролируемые test-URL;
- не обращайся к чужим ресурсам;
- проверяй, как приложение валидирует схему, hostname, MIME type и размер.

```bash
curl -s -w "\n%{http_code}" -F "file=@/dev/urandom" https://HOST/upload | tail -1
curl -s -X POST https://HOST/upload \
  -F "file=@shell.php;type=image/jpeg" | head
```

Ожидаемо:
- слишком большой файл получает `413`;
- поддельный MIME даёт ответ вроде `{"error":"Invalid file type"}`.

---

## 8.4 Практика по сценариям

### Сценарий 1: Логин и reset

Проверь:
- одинаково ли система отвечает на существующего и несуществующего пользователя;
- нет ли слишком подробных ошибок;
- что reset token не живёт слишком долго.

```bash
curl -s -X POST https://HOST/login -H 'Content-Type: application/json' \
  -d '{"email":"exists@example.com","password":"wrong"}' | jq .error
curl -s -X POST https://HOST/login -H 'Content-Type: application/json' \
  -d '{"email":"notexists@example.com","password":"wrong"}' | jq .error
```

Правильный результат:

```
"Invalid credentials"
"Invalid credentials"
```

Если ответы разные, у тебя снова user enumeration.

### Сценарий 2: Форма ввода и рендер

Проверь:
- где ввод пользователя возвращается на экран;
- нет ли `innerHTML`-подобных опасных паттернов;
- не ломает ли CSP работу приложения.

### Сценарий 3: API и CORS

Проверь:
- какие origin реально разрешены;
- нет ли `*` там, где есть cookies или auth context;
- не доверяет ли backend произвольным proxy headers.

---

## 8.5 Что фиксировать после проверки

После каждого controlled test запиши:
- что именно проверялось;
- какой был ожидаемый результат;
- где это подтвердилось в DevTools, логах или конфиге;
- что осталось слабым местом.

---

## 8.6 Чеклист главы

- [ ] Я умею проверять cookie flags и security headers
- [ ] Я могу сделать controlled check на рендер недоверенного ввода в своей lab
- [ ] Я знаю, как проверять CORS и auth flow без offensive-перекоса
- [ ] Я фиксирую результаты проверок, а не просто "пощёлкал руками"
