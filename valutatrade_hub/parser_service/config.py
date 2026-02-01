"""
Конфигурация для Parser Service.
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple

from ..infra.settings import settings


@dataclass
class ParserConfig:
    """Конфигурация парсера."""

    # API ключи (из переменных окружения)
    EXCHANGERATE_API_KEY: str = settings.get("exchangerate_api_key", "")

    # Эндпоинты API
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Базовая валюта для фиатных курсов
    BASE_CURRENCY: str = "USD"

    # Списки отслеживаемых валют
    FIAT_CURRENCIES: Tuple[str, ...] = ("EUR", "GBP", "RUB", "JPY", "CNY")
    CRYPTO_CURRENCIES: Tuple[str, ...] = ("BTC", "ETH", "SOL", "BNB", "XRP")

    # Сопоставление кодов криптовалют с ID CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BNB": "binancecoin",
        "XRP": "ripple",
    })

    # Сопоставление ID CoinGecko с кодами валют (обратное)
    ID_TO_CODE_MAP: Dict[str, str] = field(default_factory=lambda: {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "binancecoin": "BNB",
        "ripple": "XRP",
    })

    # Пути к файлам
    RATES_FILE_PATH: str = settings.get_data_path("rates.json")
    HISTORY_FILE_PATH: str = settings.get_data_path("exchange_rates.json")

    # Параметры запросов
    REQUEST_TIMEOUT: int = settings.get("coingecko_timeout", 10)
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # секунды

    # Интервал обновления (секунды)
    UPDATE_INTERVAL: int = settings.get("parser_interval_minutes", 15) * 60

    @property
    def has_exchangerate_key(self) -> bool:
        """Проверяет, установлен ли API ключ для ExchangeRate."""
        return bool(self.EXCHANGERATE_API_KEY.strip())

    @property
    def exchangerate_url(self) -> str:
        """Полный URL для ExchangeRate API."""
        if not self.has_exchangerate_key:
            raise ValueError("API ключ для ExchangeRate не установлен")
        return f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{self.BASE_CURRENCY}"

    def validate(self) -> None:
        """Проверяет валидность конфигурации."""
        if not self.has_exchangerate_key:
            print("Предупреждение: API ключ для ExchangeRate не установлен. Фиатные курсы не будут обновляться.")

        if not self.CRYPTO_CURRENCIES:
            print("Предупреждение: Список криптовалют пуст.")

        if not self.FIAT_CURRENCIES:
            print("Предупреждение: Список фиатных валют пуст.")


# Глобальный экземпляр конфигурации
config = ParserConfig()
