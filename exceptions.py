class InaccessibleVariablesError(Exception):
    """Кастомное исключение созданное для фукнции порверки переменных."""


class IncorrectServerResponseError(Exception):
    """Исключение неправильного ответа сервера."""


class InvalidResponseError(Exception):
    """Исключение - ответ API не соответствует документации."""


class WrongHomeWorkDataError(Exception):
    """Неверный статус домашней работы."""


class TelegramSendMessageError(Exception):
    """Не получилось отправить сообщение."""

UNEXPECTED_DATA='Неожиданный тип данных: {type(response["homeworks"])}'
UNEXPECTED_TYPE='Неожиданный тип данных:{type(response)!=dict}'