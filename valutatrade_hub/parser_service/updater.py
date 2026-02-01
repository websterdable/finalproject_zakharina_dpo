"""
Основной модуль обновления курсов.
"""
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..core.exceptions import ApiRequestError
from .api_clients import CoinGeckoClient, ExchangeRateApiClient, MockApiClient
from .config import config
from .storage import ParserStorage


class RatesUpdater:
    """Координатор обновления курсов."""

    def __init__(self, use_mock: bool = False):
        """
        Инициализирует обновлятель курсов.

        Args:
            use_mock: Использовать мок-клиенты для тестирования
        """
        self.logger = logging.getLogger(__name__)

        if use_mock or not config.has_exchangerate_key:
            self.clients = [MockApiClient()]
        else:
            self.clients = [
                CoinGeckoClient(),
                ExchangeRateApiClient()
            ]

        self.storage = ParserStorage()

    def run_update(self, source_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Выполняет обновление курсов.

        Args:
            source_filter: Фильтр по источнику ('coingecko' или 'exchangerate')

        Returns:
            Результат обновления
        """
        self.logger.info("Starting rates update...")

        all_rates = {}
        results = {
            "success": [],
            "failed": [],
            "total_rates": 0
        }

        for client in self.clients:
            client_name = client.__class__.__name__

            # Применяем фильтр по источнику если указан
            if source_filter:
                source_lower = source_filter.lower()
                if 'mock' in client_name.lower() and source_lower != 'mock':
                    continue
                elif 'coingecko' in client_name.lower() and source_lower != 'coingecko':
                    continue
                elif 'exchangerate' in client_name.lower() and source_lower != 'exchangerate':
                    continue

            try:
                self.logger.info(f"Fetching from {client_name}...")
                start_time = time.time()

                rates = client.fetch_rates()
                fetch_time = time.time() - start_time

                if rates:
                    # Определяем источник для сохранения
                    if 'CoinGecko' in client_name:
                        source = "CoinGecko"
                    elif 'ExchangeRate' in client_name:
                        source = "ExchangeRate-API"
                    else:
                        source = "Mock"

                    # Сохраняем в кэш и историю
                    self.storage.save_rates_to_cache(rates, source)
                    self.storage.save_to_history(rates, source, {
                        "fetch_time_ms": round(fetch_time * 1000, 2),
                        "rates_count": len(rates)
                    })

                    # Объединяем с общими результатами
                    all_rates.update(rates)

                    results["success"].append({
                        "source": source,
                        "rates_count": len(rates),
                        "fetch_time_ms": round(fetch_time * 1000, 2)
                    })
                    results["total_rates"] += len(rates)

                    self.logger.info(f"  OK: {len(rates)} rates from {source} "
                                   f"(took {fetch_time:.2f}s)")
                else:
                    self.logger.warning(f"  No rates received from {client_name}")
                    results["failed"].append({
                        "source": client_name,
                        "reason": "No rates received"
                    })

            except ApiRequestError as e:
                self.logger.error(f"  Failed: {e}")
                results["failed"].append({
                    "source": client_name,
                    "reason": str(e)
                })
            except Exception as e:
                self.logger.error(f"  Unexpected error: {e}")
                results["failed"].append({
                    "source": client_name,
                    "reason": f"Unexpected error: {e}"
                })

        # Обновляем итоговую статистику
        results["timestamp"] = datetime.now().isoformat()
        results["all_rates_count"] = len(all_rates)

        # Логируем итоги
        if results["success"]:
            self.logger.info(f"Update successful. Total rates: {results['total_rates']}")
        else:
            self.logger.warning("Update completed with errors")

        return results

    def get_update_status(self) -> Dict[str, Any]:
        """
        Получает статус последнего обновления.

        Returns:
            Статус обновления
        """
        rates_cache = self.storage.get_latest_rates()

        last_refresh = rates_cache.get("last_refresh")
        pairs_count = len(rates_cache.get("pairs", {}))

        status = {
            "last_refresh": last_refresh,
            "pairs_count": pairs_count,
            "sources": []
        }

        # Собираем информацию по источникам
        if pairs_count > 0:
            sources = {}
            for pair_data in rates_cache.get("pairs", {}).values():
                source = pair_data.get("source", "Unknown")
                sources[source] = sources.get(source, 0) + 1

            for source, count in sources.items():
                status["sources"].append({
                    "name": source,
                    "rates_count": count
                })

        return status
