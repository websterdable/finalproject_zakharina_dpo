"""
Декораторы для логирования операций.
"""
import functools
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional


def log_action(
    action_name: Optional[str] = None,
    verbose: bool = False
) -> Callable:
    """
    Декоратор для логирования операций.

    Args:
        action_name: Название операции (если None, используется имя функции)
        verbose: Подробное логирование с дополнительным контекстом
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Определяем название операции
            operation = action_name or func.__name__.upper()

            # Собираем базовый контекст
            context: Dict[str, Any] = {
                "action": operation,
                "timestamp": datetime.now().isoformat(),
            }

            # Пытаемся извлечь username/user_id из аргументов
            for arg in args:
                if hasattr(arg, 'username'):
                    context['username'] = arg.username
                if hasattr(arg, '_username'):
                    context['username'] = arg._username
                if hasattr(arg, 'user_id'):
                    context['user_id'] = arg.user_id
                if hasattr(arg, '_user_id'):
                    context['user_id'] = arg._user_id

            # Извлекаем валюту и сумму из kwargs
            if 'currency_code' in kwargs:
                context['currency'] = kwargs['currency_code']
            if 'amount' in kwargs:
                context['amount'] = kwargs['amount']

            start_time = time.time()
            result = "OK"
            error_info = None

            try:
                # Выполняем функцию
                return_value = func(*args, **kwargs)

                # Если verbose, добавляем контекст результата
                if verbose and return_value and hasattr(return_value, '__dict__'):
                    for attr in ['balance', 'rate', 'total_value']:
                        if hasattr(return_value, attr):
                            context[attr] = getattr(return_value, attr)

                return return_value

            except Exception as e:
                result = "ERROR"
                error_info = {
                    "type": type(e).__name__,
                    "message": str(e)
                }
                context['error'] = error_info
                raise

            finally:
                # Вычисляем время выполнения
                execution_time = (time.time() - start_time) * 1000  # в миллисекундах
                context['execution_ms'] = f"{execution_time:.2f}"
                context['result'] = result

                # Формируем сообщение для лога
                log_message = f"{operation}"
                if 'username' in context:
                    log_message += f" user='{context['username']}'"
                if 'currency' in context:
                    log_message += f" currency='{context['currency']}'"
                if 'amount' in context:
                    log_message += f" amount={context['amount']:.4f}"
                if 'rate' in context:
                    log_message += f" rate={context['rate']:.2f}"
                log_message += f" result={result} time={context['execution_ms']}ms"

                if result == "OK":
                    logging.info(log_message)
                else:
                    logging.error(f"{log_message} error={error_info}")

        return wrapper

    return decorator


def validate_amount(func: Callable) -> Callable:
    """Декоратор для валидации суммы."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'amount' in kwargs:
            amount = kwargs['amount']
            if not isinstance(amount, (int, float)):
                raise ValueError("Сумма должна быть числом")
            if amount <= 0:
                raise ValueError("Сумма должна быть положительным числом")
        return func(*args, **kwargs)
    return wrapper
