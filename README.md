# KATYAX

Бот поддержки автономной поддержки пользователей в Telegram. <br>
В качестве работы необходим список возможных вопросов и решений, описанных текстом. <br>
Бот должен уметь отвечать на вопросы, заданные пользователем, и предлагать общение с оператором, если ответа на вопрос нет.

## Установка

### Сборка образа контейнера

```bash
docker-compose build
```

### Запуск контейнера

```bash
docker-compose up -d
```

### Остановка контейнера

```bash
docker-compose down
```

### Удаление контейнера

```bash
docker rm katyax
docker rm webserver
```

### Удаление образа контейнера

```bash
docker rmi katyax
docker rmi webserver
```

## Настройка

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
| --- | --- | --- |
| `BOT_TOKEN ` | Токен бота | `None` |
| `SENTENCE_TRANSFORMERS_HOME` | Путь к кэшу моделей `transformers` | `.cache` |
| `ANSWERS_FILE` | Путь к файлу с ответами | `answers.md` |
| `SQLITE_DB` | Путь к базе данных SQLite | `katyax.sqlite` |
| `FLASK_SECRET` | Секретный ключ для Flask | `mysupersecret!key` |
| `FLAST_HOST` | Хост для Flask | `127.0.0.1` |
| `REMOTE_ADDR` | IP адрес для Flask | `0.0.0.0` |
| `FLASK_PORT` | Порт для Flask | `5000` |
| `FLASK_DEBUG` | Режим отладки для Flask | `False` |
| `TOKEN_EXPIRE_MINUTES` | Время жизни токена в минутах | `60` |