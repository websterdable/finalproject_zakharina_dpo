"""
Вспомогательные функции для работы с валютами и валидации.
"""
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .currencies import get_all_currencies


def validate_currency_code(code: str) -> str:
    """
    Валидирует код валюты.

    Args:
        code: Код валюты

    Returns:
        Валидный код в верхнем регистре

    Raises:
        ValueError: Если код невалиден
    """
    if not code or not isinstance(code, str):
        raise ValueError("Код валюты должен быть строкой")

    code = code.strip().upper()

    # Проверка формата
    if not re.match(r'^[A-Z]{2,5}$', code):
        raise ValueError(
            f"Код валюты '{code}' должен содержать 2-5 букв в верхнем регистре"
        )

    # Проверка существования в реестре (опционально, но желательно)
    try:
        currencies = get_all_currencies()
        if code not in currencies:
            # Для гибкости не выбрасываем исключение, только предупреждение
            pass
    except Exception:
        pass

    return code


def validate_amount(amount: float) -> float:
    """
    Валидирует сумму.

    Args:
        amount: Сумма

    Returns:
        Валидная сумма

    Raises:
        ValueError: Если сумма невалидна
    """
    if not isinstance(amount, (int, float)):
        raise ValueError("Сумма должна быть числом")

    amount = float(amount)

    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")

    # Ограничение на слишком большие суммы
    if amount > 1_000_000_000:  # 1 миллиард
        raise ValueError("Сумма слишком велика")

    return amount


def format_currency_value(value: float, currency_code: str) -> str:
    """
    Форматирует денежное значение.

    Args:
        value: Значение
        currency_code: Код валюты

    Returns:
        Отформатированная строка
    """
    # Определяем количество знаков после запятой
    if currency_code in ["BTC", "ETH", "SOL"]:
        # Криптовалюты - 8 знаков
        formatted = f"{value:.8f}"
    elif currency_code in ["JPY", "KRW"]:
        # Валюты с маленькой стоимостью - 2 знака
        formatted = f"{value:.2f}"
    else:
        # Остальные - 4 знака
        formatted = f"{value:.4f}"

    # Убираем лишние нули
    formatted = formatted.rstrip('0').rstrip('.')

    return f"{formatted} {currency_code}"


def parse_currency_pair(pair_str: str) -> Tuple[str, str]:
    """
    Парсит строку пары валют (например, "USD/EUR" или "BTC_USD").

    Args:
        pair_str: Строка с парой валют

    Returns:
        Кортеж (from_currency, to_currency)

    Raises:
        ValueError: Если строка невалидна
    """
    if not pair_str or not isinstance(pair_str, str):
        raise ValueError("Строка пары валют должна быть непустой строкой")

    # Пробуем разные разделители
    for separator in ['/', '_', '-']:
        if separator in pair_str:
            parts = pair_str.split(separator)
            if len(parts) == 2:
                from_curr = validate_currency_code(parts[0])
                to_curr = validate_currency_code(parts[1])
                return from_curr, to_curr

    # Если разделитель не найден, предполагаем что это 6 символов (например, "USDEUR")
    if len(pair_str) == 6:
        from_curr = validate_currency_code(pair_str[:3])
        to_curr = validate_currency_code(pair_str[3:])
        return from_curr, to_curr

    raise ValueError(f"Не удалось распарсить валютную пару: {pair_str}")


def is_rate_fresh(updated_at: str, ttl_seconds: int = 300) -> bool:
    """
    Проверяет, свежий ли курс.

    Args:
        updated_at: Время обновления в ISO формате
        ttl_seconds: Время жизни кэша в секундах

    Returns:
        True если курс свежий, False если устарел
    """
    try:
        update_time = datetime.fromisoformat(updated_at)
        now = datetime.now()
        age = (now - update_time).total_seconds()
        return age <= ttl_seconds
    except (ValueError, TypeError):
        return False


def get_currency_list() -> str:
    """Возвращает список всех доступных валют."""
    currencies = get_all_currencies()
    result = []

    for code, currency in currencies.items():
        result.append(f"{code}: {currency.name}")

    return "\n".join(sorted(result))


def calculate_conversion(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates_cache: Dict[str, Any]
) -> Optional[float]:
    """
    Рассчитывает конвертацию суммы.

    Args:
        amount: Сумма для конвертации
        from_currency: Исходная валюта
        to_currency: Целевая валюта
        rates_cache: Кэш курсов

    Returns:
        Результат конвертации или None если курс недоступен
    """
    if from_currency == to_currency:
        return amount

    # Прямой курс
    pair_key = f"{from_currency}_{to_currency}"
    if pair_key in rates_cache:
        rate = rates_cache[pair_key].get("rate")
        if rate:
            return amount * rate

    # Обратный курс
    reverse_key = f"{to_currency}_{from_currency}"
    if reverse_key in rates_cache:
        rate = rates_cache[reverse_key].get("rate")
        if rate:
            return amount / rate

    # Через USD (если обе валюты имеют курс к USD)
    usd_rates = {}
    for key in rates_cache.keys():
        if key.endswith("_USD"):
            usd_rates[key.replace("_USD", "")] = rates_cache[key].get("rate")
        elif key.startswith("USD_"):
            usd_rates[key.replace("USD_", "")] = 1 / rates_cache[key].get("rate") if rates_cache[key].get("rate") else None

    if from_currency in usd_rates and to_currency in usd_rates:
        if usd_rates[from_currency] and usd_rates[to_currency]:
            # Конвертируем from -> USD -> to
            usd_amount = amount * usd_rates[from_currency]
            return usd_amount / usd_rates[to_currency]

    return None
