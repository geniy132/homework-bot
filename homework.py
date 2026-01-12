import logging
import os
import sys
import time
from contextlib import suppress
from functools import wraps
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import telebot, TeleBot

from exceptions import (
    ApiRequestError,
    ProgramErrorsException
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность перемнных, необходимых для работы программы."""
    tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = [token for token in tokens if not globals()[token]]
    missing_tokens_message = (
        'Отсутствует обязательная переменная окружения: '
        f'{", ".join(missing_tokens)}\n'
        'Программа принудительно остановлена.'
    )
    if missing_tokens:
        logging.critical(missing_tokens_message)
        raise ValueError(missing_tokens_message)


def deduplicate_messages(func):
    """Функция-декоратор для send_message."""
    last_sent_message = None

    @wraps(func)
    def wrapper(bot, message):
        """Проверяем сообщение на дубль."""
        nonlocal last_sent_message
        if message != last_sent_message:
            func(bot, message)
            last_sent_message = message
        else:
            logging.debug(f'Сообщение {message} совпало с предыдущим.')
    return wrapper


@deduplicate_messages
def send_message(bot, message):
    """Отправляем сообщение в Telegram-чат."""
    logging.debug(f'Бот начал отправку сообщения {message}')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logging.debug(f'Бот отправил сообщение {message}')


def get_api_answer(timestamp):
    """Делаем запрос к эндпоинту."""
    params = {'from_date': timestamp}
    logging.debug(f'Отправляем запрос к {ENDPOINT} с параметрами: {params}')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise ApiRequestError(f'Ошибка при выполнении запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        raise ApiRequestError('Сбой в работе программы: Эндпоинт недоступен. '
                              f'Код ответа API: {response.status_code}')
    logging.debug('Запрос выполнен успешно, получаем ответ.')
    return response.json()


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    logging.debug('Начинаем проверку ответа API.')
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является словарем, '
                        f'получен тип: {type(response)}')
    if 'homeworks' not in response:
        raise ValueError('В ответе API отсутствует ключ "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Данные под ключом "homeworks" не являются списком, '
                        f'получен тип: {type(response['homeworks'])}')
    logging.debug('Проверка ответа API успешно завершена.')


def parse_status(homework):
    """Извлекаем статус домашней работы."""
    logging.debug(f'Начинаем извлечение статуса домашней работы {homework}.')
    keys = ['homework_name', 'status']
    missing_keys = set(keys) - set(homework.keys())
    if missing_keys:
        raise KeyError('В ответе отсутствуют обязательные ключи: '
                       f'{", ".join(missing_keys)}.')
    homework_name = homework['homework_name']
    status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError(
            f'Неожиданный статус ({status}) домашней работы "{homework_name}"'
        )
    logging.debug('Статус домашней работы '
                  f'{homework} успешно получен ({status}).')
    return (f'Изменился статус проверки работы "{homework_name}". '
            f'{verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if not response['homeworks']:
                logging.debug('Список домашних работ пуст.')
                continue
            homework = response['homeworks'][-1]
            message = parse_status(homework)
            send_message(bot, message)
            timestamp = response.get('current_date', timestamp)
        except (
            telebot.apihelper.ApiException,
            requests.exceptions.RequestException,
            ProgramErrorsException
        ) as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            with suppress(ProgramErrorsException):
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

    logging.basicConfig(
        handlers=(
            logging.StreamHandler(),
            logging.FileHandler('bot.log', mode='w', encoding='utf-8')
        ),
        format='%(asctime)s, %(levelname)s, %(message)s',
        level=logging.DEBUG,
        stream=sys.stdout,
    )
