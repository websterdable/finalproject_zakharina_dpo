"""
Операции чтения/записи данных парсера.
"""
from datetime import datetime
from typing import Any, Dict, List

from ..infra.database import db


class ParserStorage:
    """Управление хранением данных парсера."""

    @staticmethod
    def save_rates_to_cache(rates: Dict[str, float], source: str) -> None:
        """
        Сохраняет курсы в кэш (rates.json).

        Args:
            rates: Словарь с курсами {валютная_пара: курс}
            source: Источник данных
        """
        current_rates = db.get_rates()
        pairs = current_rates.get("pairs", {})
        timestamp = datetime.now().isoformat()

        # Обновляем пары
        for pair_key, rate in rates.items():
            if rate and rate > 0:
                pairs[pair_key] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": source
                }

        # Сохраняем
        current_rates["pairs"] = pairs
        current_rates["last_refresh"] = timestamp
        current_rates["source"] = source

        db.save_rates(current_rates)

    @staticmethod
    def save_to_history(
        rates: Dict[str, float],
        source: str,
        meta: Dict[str, Any] = None
    ) -> None:
        """
        Сохраняет курсы в историю (exchange_rates.json).

        Args:
            rates: Словарь с курсами
            source: Источник данных
            meta: Дополнительные метаданные
        """
        timestamp = datetime.now().isoformat()

        for pair_key, rate in rates.items():
            if rate and rate > 0:
                # Разбиваем пару на валюты
                parts = pair_key.split('_')
                if len(parts) == 2:
                    from_currency, to_currency = parts

                    record = {
                        "id": f"{pair_key}_{timestamp}",
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": source,
                        "meta": meta or {}
                    }

                    db.append_to_history(record)

    @staticmethod
    def get_history(
        from_currency: str = None,
        to_currency: str = None,
        source: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает историю курсов с фильтрами.

        Args:
            from_currency: Фильтр по исходной валюте
            to_currency: Фильтр по целевой валюте
            source: Фильтр по источнику
            limit: Максимальное количество записей

        Returns:
            Список записей истории
        """
        history = db.get_exchange_rates_history()
        filtered = []

        for record in history:
            if from_currency and record.get("from_currency") != from_currency:
                continue
            if to_currency and record.get("to_currency") != to_currency:
                continue
            if source and record.get("source") != source:
                continue

            filtered.append(record)

        # Сортируем по времени (новые первыми)
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return filtered[:limit]

    @staticmethod
    def get_latest_rates() -> Dict[str, Any]:
        """
        Получает последние курсы из кэша.

        Returns:
            Словарь с последними курсами
        """
        return db.get_rates()

    @staticmethod
    def clear_old_history(days_to_keep: int = 30) -> None:
        """
        Удаляет старые записи из истории.

        Args:
            days_to_keep: Количество дней для хранения
        """
        history = db.get_exchange_rates_history()
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)

        filtered = []
        for record in history:
            try:
                record_time = datetime.fromisoformat(record.get("timestamp", "")).timestamp()
                if record_time > cutoff_date:
                    filtered.append(record)
            except (ValueError, TypeError):
                # Пропускаем некорректные записи
                pass

        db.save_exchange_rates_history(filtered)

    @staticmethod
    def get_rate_statistics(pair_key: str) -> Dict[str, Any]:
        """
        Получает статистику по валютной паре.

        Args:
            pair_key: Ключ валютной пары (например, "BTC_USD")

        Returns:
            Статистика
        """
        history = db.get_exchange_rates_history()

        pair_history = []
        for record in history:
            if f"{record.get('from_currency')}_{record.get('to_currency')}" == pair_key:
                pair_history.append(record)

        if not pair_history:
            return {}

        # Сортируем по времени
        pair_history.sort(key=lambda x: x.get("timestamp", ""))

        rates = [record.get("rate", 0) for record in pair_history]

        return {
            "pair": pair_key,
            "count": len(rates),
            "min": min(rates) if rates else 0,
            "max": max(rates) if rates else 0,
            "avg": sum(rates) / len(rates) if rates else 0,
            "latest": rates[-1] if rates else 0,
            "first_timestamp": pair_history[0].get("timestamp") if pair_history else None,
            "last_timestamp": pair_history[-1].get("timestamp") if pair_history else None,
        }
