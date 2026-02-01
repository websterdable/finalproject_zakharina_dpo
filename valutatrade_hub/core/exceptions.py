"""
Пользовательские исключения для доменной логики.
"""

class ValutaTradeError(Exception):
    """Базовое исключение для всех ошибок приложения."""
    pass


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств на кошельке."""
    def __init__(self, code: str, available: float, required: float):
        self.code = code
        self.available = available
        self.required = required
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, требуется {required:.4f} {code}"
        )


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Ошибка при обращении к внешнему API."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class UserNotFoundError(ValutaTradeError):
    """Пользователь не найден."""
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class AuthenticationError(ValutaTradeError):
    """Ошибка аутентификации."""
    def __init__(self, message: str = "Неверный логин или пароль"):
        super().__init__(message)


class PortfolioNotFoundError(ValutaTradeError):
    """Портфель пользователя не найден."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Портфель для пользователя с ID={user_id} не найден")
