import requests
import os
from dotenv import load_dotenv
import logging
import time

from http import HTTPStatus
import telegram

import exceptions


load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность необходимых переменных окружения.
    Фукнция сразу останавливает программу, если замечает
    недоступность переменной окружения.
    """
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key in tokens.keys():
        if tokens[key] is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {key}'
            )
            exit(f'Недоступна переменная окружения: {key}')
        else:
            logging.info(f'Все переменные окружения доступны: {tokens}')


def send_message(bot: telegram.bot.Bot, message: str) -> None:
    """Принимает экземпляр бота и готовую строку.
    Отправляет сообщение со стокой в телеграмм.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Отправил сообщение: {message}')
    except telegram.error.TelegramError as error:
        logging.error(
            f'Сбой при отправке сообщения в Telegram - {error}',
            exc_info=True
        )
        raise exceptions.TelegramSendMessageError(
            f'Не удалось отправить сообщение: {error}'
        )


def get_api_answer(timestamp: int) -> dict:
    """Проверяет доступность эндпоинта."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Недоступность экнпоинта: {ENDPOINT}, {response.status_code}',
                exc_info=True
            )
            raise exceptions.IncorrectServerResponseError(
                f'Недоступность экнпоинта: {response.status_code}'
            )
        else:
            logging.debug(f'Корректный ответ сервера: {response.status_code}')
            return response.json()
    except requests.RequestException as error:
        logging.error(
            f'Недоступность экнпоинта: {ENDPOINT}, {error}',
            exc_info=True
        )


def check_response(response: dict) -> list:
    """Функция проверки ответа API.
    Получается на вход словарь с ответом API,
    Использует импортированные константы,
    Проверяет его на соответствие документации,
    Возвращает инф. о конкретной домашке.
    """
    if isinstance(response, dict):
        if 'homeworks' not in (response).keys():
            logging.error(f'{exceptions.NOT_MATCH_DOC}', exc_info=True)
            raise exceptions.InvalidResponseError(
                f'{exceptions.NOT_MATCH_DOC}'
            )

        if not isinstance(response['homeworks'], list):
            logging.error(f'{exceptions.UNEXPECTED_DATA}')
            raise TypeError(f'{exceptions.UNEXPECTED_DATA}')
        return response['homeworks']

    else:
        logging.error(f'{exceptions.UNEXPECTED_TYPE}', exc_info=True)
        raise TypeError(f'{exceptions.UNEXPECTED_TYPE}')


def parse_status(homework: dict) -> str:
    """Вычленяет из ответа API статус и название Д.Р.
    Принимает словарь с инф. о домашней работе,
    возвращает подготовленное сообщение для отправки в ТГ
    или raise кастомную ошибку.
    """
    if homework.get('status') in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework.get('status')]
        if 'homework_name' not in homework:
            logging.error(
                'В ответе API нет ожидаемых ключей: homework_name',
                exc_info=True
            )
            raise KeyError('В ответе API нет ожидаемых ключей: homework_name')
        homework_name = homework['homework_name']
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error(
            'Неожиданый статус домашней работы, в ответе API',
            exc_info=True
        )
        raise KeyError(
            'В ответе API неожиданный статус домашней работы'
        )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_message = ''
    bug_report_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework_info = check_response(response)
            logging.debug('Ответ API соответствует документации')
            if len(homework_info) > 0:
                message = parse_status(homework_info[0])

                if current_message != message:
                    logging.debug('Замечен новый статус домашки')
                    send_message(bot, message)
                    current_message = message
                    timestamp = response.get('current_date')
                else:
                    logging.debug('Отсутствие в овтете новых статусов')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != bug_report_message:
                try:
                    send_message(bot, message)
                    bug_report_message = message
                except Exception:
                    logging.error(
                        f'Не удалось отправить сообщение об ошибке: {message}',
                        exc_info=True
                    )
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
