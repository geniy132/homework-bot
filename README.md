### Как запустить проект Homework Bot:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone 
```

```
cd homework-bot
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

* Если у вас Linux/macOS

    ```
    source venv/bin/activate
    ```

* Если у вас windows

    ```
    source venv/scripts/activate
    ```

Установить зависимости из файла requirements.txt:

```
python3 -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

Создать в директории проекта файл .env с тремя переменными окружения:

```
TOKEN=api_token
TG_TOKEN=your_bot_token
TG_CHAT_ID=your_chat_id
```

Запустить проект:

```
python homework.py
```
