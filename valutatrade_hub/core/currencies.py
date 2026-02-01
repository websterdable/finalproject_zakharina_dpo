"""
Иерархия валют: базовый класс и наследники.
"""
from abc import ABC, abstractmethod
from typing import Dict

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для валют."""

    def __init__(self, name: str, code: str):
        if not name or not isinstance(name, str):
            raise ValueError("Название валюты должно быть непустой строкой")
        if not code or not isinstance(code, str) or not code.isupper() or not 2 <= len(code) <= 5:
            raise ValueError("Код валюты должен быть строкой в верхнем регистре длиной 2-5 символов")

        self._name = name
        self._code = code

    @property
    def name(self) -> str:
        """Человекочитаемое название валюты."""
        return self._name

    @property
    def code(self) -> str:
        """Код валюты (например, 'USD', 'BTC')."""
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов."""
        pass

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, code={self.code!r})"


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        """Страна или зона эмиссии."""
        return self._issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        """Алгоритм консенсуса."""
        return self._algorithm

    @property
    def market_cap(self) -> float:
        """Рыночная капитализация."""
        return self._market_cap

    def get_display_info(self) -> str:
        mcap_str = f"{self._market_cap:,.2f}" if self._market_cap > 0 else "N/A"
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


# Реестр валют
_CURRENCY_REGISTRY: Dict[str, Currency] = {}

# Предопределенные валюты
PREDEFINED_CURRENCIES = [
    FiatCurrency("US Dollar", "USD", "United States"),
    FiatCurrency("Euro", "EUR", "Eurozone"),
    FiatCurrency("British Pound", "GBP", "United Kingdom"),
    FiatCurrency("Russian Ruble", "RUB", "Russia"),
    CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1_120_000_000_000),
    CryptoCurrency("Ethereum", "ETH", "Ethash", 450_000_000_000),
    CryptoCurrency("Solana", "SOL", "Proof of History", 65_000_000_000),
]

# Инициализация реестра
for currency in PREDEFINED_CURRENCIES:
    _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """
    Возвращает объект валюты по коду.

    Args:
        code: Код валюты (например, 'USD', 'BTC')

    Returns:
        Объект Currency

    Raises:
        CurrencyNotFoundError: Если валюта не найдена
    """
    code = code.upper()
    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)
    return _CURRENCY_REGISTRY[code]


def get_all_currencies() -> Dict[str, Currency]:
    """Возвращает копию реестра всех валют."""
    return _CURRENCY_REGISTRY.copy()


def register_currency(currency: Currency) -> None:
    """Регистрирует новую валюту в реестре."""
    _CURRENCY_REGISTRY[currency.code] = currency
