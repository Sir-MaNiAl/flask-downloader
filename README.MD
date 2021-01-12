REST API для приложения, которое загружает файлы на диск

Стэк
Flask, SQLAlchemy, PostgreSQL, Celery(rabbitmq, redis)

---
## Описание API в вольной форме
(в разработке спецификация OpenAPI)

```
objects:
  File: {'id': <str:uuid>,  # уникальный идентификатор файла
         'url': <str:url>,  # URL файла
         'added_at': <str:iso_datetime>,  # Дата и время создания задачи
         'name': <str>,  # Имя файла, берётся из источника. Можно переименовать
         'download_time': <str:time>,  # Время, потраченное на скачивание файла
         'size': <str>}  # Размер файла
```

### Поставить в очередь на закачку список URL
```
POST /download
json: {'url_list': [<str>]}

response:
  200:
    json: {'files': [<{'url': <str:url>, 'id': <str:uuid>}>]}
  422:
    json: {'description': <str>,
           'data': <request.data>,
           'errors': <request.data.validation_errors>}
```

### Просмотреть информацию о файлах постранично
```
GET /files
json: {'per_page': <int=20, optional>,
       'show_after_id': <uuid=None, optional>}

response:
  200:
    json: {'files': [<object:File>]}
  422:
    json: {'description': <str>,
           'data': <request.data>,
           'errors': <request.data.validation_errors>}
```

### Просмотреть информацию об одном файле
```
GET /file/<uuid:id>

response:
  200:
    json: <object:File> or {}
```

### Переименовать файл
```
POST /file/<uuid:1d>
json: {'name': <str>}

response:
  200:
    json: <object:File> or {}
  422:
    json: {'description': <str>,
           'data': <request.data>,
           'errors': <request.data.validation_errors>}
```

### Удалить файл
```
DELETE /file/<uuid:id>

response:
  200:
    json: {}
```

---
## Docker-compose
В корне проекта лежит файл конфигурации docker-compose. Разворачивает сервер и слушает на 8000 порту. Без TLS, для него можно развернуть поверх контейнер с реверс-прокси, например nginx.

Инфраструктура:
* web(gunicorn)
* celery
* rabbitmq
* redis
* postgresql

Ожидается монтирование директории ./upload в один из контейнеров с правами на запись и просмотр содержимого.

Все образы тянутся с hub.docker.com.
