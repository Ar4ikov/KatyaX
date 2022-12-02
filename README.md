# KATYAX

Бот поддержки автономной поддержки пользователей в Telegram. <br>
В качестве работы необходим список возможных вопросов и решений, описанных текстом. <br>
Бот должен уметь отвечать на вопросы, заданные пользователем, и предлагать общение с оператором, если ответа на вопрос нет.

## Установка

### Сборка образа контейнера

```bash
docker build -t katyax .
```

### Запуск контейнера

```bash
docker run -d --name katyax -v /local/dir/path:/katyax --env-file .env katyax
```

### Перезапуск контейнера

```bash
docker restart katyax
```

### Остановка контейнера

```bash
docker stop katyax
```

### Удаление контейнера

```bash
docker rm katyax
```

### Удаление образа контейнера

```bash
docker rmi katyax
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
| `FLASK_PORT` | Порт для Flask | `5000` |
| `FLASK_DEBUG` | Режим отладки для Flask | `False` |
| `TOKEN_EXPIRE_MINUTES` | Время жизни токена в минутах | `60` |