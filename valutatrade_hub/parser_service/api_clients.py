"""
Клиенты для работы с внешними API.
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests

from ..core.exceptions import ApiRequestError
from .config import config


class BaseApiClient(ABC):
    """Базовый класс для API клиентов."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ValutaTradeHub/1.0'
        })

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы валют.

        Returns:
            Словарь с курсами {валютная_пара: курс}

        Raises:
            ApiRequestError: При ошибке запроса
        """
        pass

    def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = config.MAX_RETRIES
    ) -> requests.Response:
        """
        Выполняет HTTP запрос с повторными попытками.

        Args:
            url: URL для запроса
            params: Параметры запроса
            max_retries: Максимальное количество попыток

        Returns:
            Ответ сервера

        Raises:
            ApiRequestError: При ошибке запроса
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                last_error = f"Таймаут запроса: {e}"
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)

            except requests.exceptions.ConnectionError as e:
                last_error = f"Ошибка подключения: {e}"
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None

                if status_code == 429:  # Too Many Requests
                    last_error = "Превышен лимит запросов (429)"
                    # Ждем дольше перед повторной попыткой
                    time.sleep(10)
                    continue
                elif status_code == 401:  # Unauthorized
                    raise ApiRequestError("Неверный API ключ (401)") from e
                elif status_code == 403:  # Forbidden
                    raise ApiRequestError("Доступ запрещен (403)") from e
                else:
                    last_error = f"HTTP ошибка {status_code}: {e}"
                    if attempt < max_retries - 1:
                        time.sleep(config.RETRY_DELAY)

            except Exception as e:
                last_error = f"Неизвестная ошибка: {e}"
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)

        # Если все попытки неудачны
        raise ApiRequestError(f"Не удалось выполнить запрос после {max_retries} попыток: {last_error}")


class CoinGeckoClient(BaseApiClient):
    """Клиент для CoinGecko API (криптовалюты)."""

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы криптовалют к USD.

        Returns:
            Словарь {CRYPTO_USD: курс}
        """
        # Получаем ID криптовалют из конфигурации
        crypto_ids = []
        for code in config.CRYPTO_CURRENCIES:
            if code in config.CRYPTO_ID_MAP:
                crypto_ids.append(config.CRYPTO_ID_MAP[code])

        if not crypto_ids:
            return {}

        # Формируем параметры запроса
        params = {
            'ids': ','.join(crypto_ids),
            'vs_currencies': 'usd'
        }

        try:
            response = self._make_request(config.COINGECKO_URL, params)
            data = response.json()

            rates = {}
            #timestamp = datetime.now().isoformat()

            for coin_id, rates_data in data.items():
                if coin_id in config.ID_TO_CODE_MAP and 'usd' in rates_data:
                    crypto_code = config.ID_TO_CODE_MAP[coin_id]
                    rate = rates_data['usd']

                    if rate and rate > 0:
                        pair_key = f"{crypto_code}_{config.BASE_CURRENCY}"
                        rates[pair_key] = rate

            return rates

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Ошибка парсинга CoinGecko: {e}") from e


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API (фиатные валюты)."""

    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы фиатных валют к USD.

        Returns:
            Словарь {FIAT_USD: курс}
        """
        if not config.has_exchangerate_key:
            raise ApiRequestError("API ключ для ExchangeRate не установлен")

        try:
            response = self._make_request(config.exchangerate_url)
            data = response.json()

            if data.get('result') != 'success':
                error_type = data.get('error-type', 'unknown')
                raise ApiRequestError(f"ExchangeRate API error: {error_type}")

            base_code = data.get('base_code', 'USD')
            rates_data = data.get('conversion_rates', {})

            if not rates_data:
                rates_data = data.get('rates', {})

            rates = {}

            for fiat_code in config.FIAT_CURRENCIES:
                if fiat_code in rates_data and fiat_code != base_code:
                    rate = rates_data[fiat_code]

                    if rate and rate > 0:
                        # Конвертируем к курсу fiat->USD
                        # В ответе rates это base->target, нам нужно target->base
                        if base_code == 'USD':
                            # Если база USD, то rate уже fiat->USD
                            pair_key = f"{fiat_code}_USD"
                            rates[pair_key] = rate
                        else:
                            # Нужно конвертировать
                            # TODO: Более сложная логика конвертации
                            pass

            # Также добавляем курсы для других пар между фиатными валютами
            for from_curr in config.FIAT_CURRENCIES:
                for to_curr in config.FIAT_CURRENCIES:
                    if from_curr != to_curr:
                        if from_curr in rates_data and to_curr in rates_data:
                            # Конвертируем через USD
                            rate_from_usd = 1 / rates_data[from_curr] if from_curr != 'USD' else 1
                            rate_to_usd = rates_data[to_curr] if to_curr != 'USD' else 1

                            if rate_from_usd and rate_to_usd:
                                pair_key = f"{from_curr}_{to_curr}"
                                rates[pair_key] = rate_from_usd * rate_to_usd

            return rates

        except ApiRequestError:
            raise
        except Exception as e:
            raise ApiRequestError(f"Ошибка парсинга ExchangeRate: {e}") from e


class MockApiClient(BaseApiClient):
    """Мок-клиент для тестирования (использует фиктивные данные)."""

    def fetch_rates(self) -> Dict[str, float]:
        """Возвращает фиктивные курсы для тестирования."""
        rates = {}

        # Фиктивные курсы криптовалют
        crypto_rates = {
            "BTC_USD": 59337.21,
            "ETH_USD": 3720.00,
            "SOL_USD": 145.12,
            "BNB_USD": 580.50,
            "XRP_USD": 0.52,
        }

        # Фиктивные курсы фиатных валют
        fiat_rates = {
            "EUR_USD": 1.0786,
            "GBP_USD": 1.2567,
            "RUB_USD": 0.01016,
            "JPY_USD": 0.0067,
            "CNY_USD": 0.138,
        }

        rates.update(crypto_rates)
        rates.update(fiat_rates)

        return rates
