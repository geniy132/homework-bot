import logging
import os
import requests
import sys
import time

from telebot import TeleBot
from dotenv import load_dotenv


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
PREVIOUS_STATUS = None

logging.basicConfig(
    filename='bot.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s',
    level=logging.DEBUG,
    encoding='utf-8',
)
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


def check_tokens():
    """Проверяем доступность перемнных, необходимых для работы программы."""
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if not token:
            logging.critical(f'Отсутствует обязательная переменная окружения: '
                             f'{token}\nПрограмма принудительно остановлена.')
            return False
    return True


def send_message(bot, message):
    """Отправляем сообщение в Telegram-чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делаем запрос к эндпоинту."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f'Сбой в работе программы: Эндпоинт недоступен. '
                          f'Код ответа API: {response.status_code}')
            raise Exception
    except Exception as error:
        logging.error(f'Ошибка при выполнении запроса: {error}')
        raise Exception


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('Ответ API не является словарем')
        raise TypeError
    expected_keys = {'homeworks', 'current_date'}
    if not expected_keys.issubset(response.keys()):
        missing_keys = expected_keys - set(response.keys())
        logging.error(f'В ответе API отсутствуют ключи: {missing_keys}')
        raise ValueError
    if not isinstance(response['homeworks'], list):
        logging.error('Данные под ключом "homeworks" не являются списком')
        raise TypeError
    if len(response['homeworks']) == 0:
        logging.debug('Список домашних работ пуст.')
        return True
    return True


def parse_status(homework):
    """Извлекаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status, 'Статус неизвестен')
    if homework_name is None:
        logging.debug('В ответе отсутствует ключ "homework_name".')
        raise ValueError
    elif status is None:
        logging.debug(
            f'В ответе отсутствует статус для работы "{homework_name}".'
        )
        raise ValueError
    elif verdict == 'Статус неизвестен':
        logging.debug(
            f'Неожиданный статус ({status}) домашней работы "{homework_name}"'
        )
        raise ValueError
    else:
        global PREVIOUS_STATUS
        if status == PREVIOUS_STATUS:
            logging.debug(f'Статус работы "{homework_name}" не изменился.')
            return 'Статус не изменился.'
        else:
            PREVIOUS_STATUS = status
            return (
                f'Изменился статус проверки работы "{homework_name}". '
                f'{verdict}'
            )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return 'Программа остановлена'
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0

    while True:
        try:
            response = get_api_answer(timestamp)
            if response:
                if check_response(response):
                    homework = response['homeworks'][-1]
                    message = parse_status(homework)
                    send_message(bot, message)
                    timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
