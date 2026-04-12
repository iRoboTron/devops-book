# Приложение A: Шпаргалка команд Docker

> Все команды из книги в одной таблице.

---

## Docker — контейнеры

| Команда | Что делает |
|---------|-----------|
| `docker run IMAGE` | Запустить контейнер |
| `docker run -d --name X IMAGE` | В фоне с именем |
| `docker run -it IMAGE bash` | Интерактивный режим |
| `docker run -p 8080:80 IMAGE` | Проброс порта |
| `docker run --rm IMAGE` | Удалить после остановки |
| `docker run -v vol:/path IMAGE` | Том |
| `docker run -e VAR=val IMAGE` | Переменная окружения |
| `docker run --network NET IMAGE` | Сеть |
| `docker ps` | Запущенные контейнеры |
| `docker ps -a` | Все контейнеры |
| `docker stop NAME` | Остановить |
| `docker start NAME` | Запустить |
| `docker restart NAME` | Перезапустить |
| `docker rm NAME` | Удалить |
| `docker rm -f NAME` | Удалить принудительно |
| `docker logs NAME` | Логи |
| `docker logs -f NAME` | Следить за логами |
| `docker exec -it NAME bash` | Зайти внутрь |
| `docker inspect NAME` | Подробная информация |

## Docker — образы

| Команда | Что делает |
|---------|-----------|
| `docker pull IMAGE:TAG` | Скачать образ |
| `docker images` | Список образов |
| `docker rmi IMAGE` | Удалить образ |
| `docker build -t NAME .` | Собрать образ |
| `docker build --no-cache .` | Без кэша |
| `docker history IMAGE` | Слои образа |
| `docker image prune` | Удалить неиспользуемые |
| `docker image prune -a` | Удалить все неиспользуемые |
| `docker tag OLD NEW` | Переименовать тег |
| `docker push IMAGE` | Загрузить в реестр |

## Docker — тома

| Команда | Что делает |
|---------|-----------|
| `docker volume create NAME` | Создать том |
| `docker volume ls` | Список томов |
| `docker volume inspect NAME` | Информация о томе |
| `docker volume rm NAME` | Удалить том |
| `docker volume prune` | Удалить неиспользуемые |

## Docker — сети

| Команда | Что делает |
|---------|-----------|
| `docker network create NAME` | Создать сеть |
| `docker network ls` | Список сетей |
| `docker network inspect NAME` | Информация о сети |
| `docker network rm NAME` | Удалить сеть |
| `docker network prune` | Удалить неиспользуемые |
| `docker network connect NET CONTAINER` | Подключить контейнер |
| `docker network disconnect NET CONTAINER` | Отключить контейнер |

## Docker Compose

| Команда | Что делает |
|---------|-----------|
| `docker compose up -d` | Поднять стек |
| `docker compose up -d --build` | Пересобрать и поднять |
| `docker compose down` | Остановить и удалить |
| `docker compose down -v` | И тома тоже (осторожно!) |
| `docker compose ps` | Статус сервисов |
| `docker compose logs` | Все логи |
| `docker compose logs -f SERVICE` | Логи сервиса в реальном времени |
| `docker compose exec SERVICE bash` | Зайти в сервис |
| `docker compose restart SERVICE` | Перезапустить сервис |
| `docker compose config` | Показать конфиг с переменными |
| `docker compose build` | Пересобрать образы |
| `docker compose pull` | Скачать образы |

## Docker — очистка

| Команда | Что делает |
|---------|-----------|
| `docker container prune` | Удалить остановленные контейнеры |
| `docker image prune` | Удалить dangling образы |
| `docker volume prune` | Удалить неиспользуемые тома |
| `docker network prune` | Удалить неиспользуемые сети |
| `docker system prune` | Всё вышеперечисленное |
| `docker system prune -a` | Всё + все неиспользуемые образы |
| `docker system df` | Сколько места занимает Docker |
| `docker system df -v` | Подробно |
