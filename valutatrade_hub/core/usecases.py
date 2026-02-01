"""
Бизнес-логика приложения: регистрация, вход, операции с валютами.
"""
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..decorators import log_action
from ..infra.database import db
from ..infra.settings import settings
from .currencies import CurrencyNotFoundError, get_currency
from .exceptions import (
    ApiRequestError,
    AuthenticationError,
    InsufficientFundsError,
    PortfolioNotFoundError,
    UserNotFoundError,
)
from .models import Portfolio, User, Wallet
from .utils import is_rate_fresh, validate_amount, validate_currency_code


class UserUseCase:
    """Бизнес-логика для работы с пользователями."""

    @staticmethod
    @log_action("REGISTER", verbose=True)
    def register(username: str, password: str) -> User:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Созданный пользователь

        Raises:
            ValueError: Если имя пользователя уже занято
        """
        # Проверяем уникальность имени
        existing_user = db.get_user_by_username(username)
        if existing_user:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

        # Создаем пользователя
        user = User.create(username, password)
        user_id = db.get_next_user_id()

        # Присваиваем ID (не идеально, но работает)
        user._user_id = user_id

        # Сохраняем пользователя
        users = db.get_users()
        users.append(user.to_dict())
        db.save_users(users)

        # Создаем пустой портфель
        portfolios = db.get_portfolios()
        portfolios.append({
            "user_id": user_id,
            "wallets": {}
        })
        db.save_portfolios(portfolios)

        return user

    @staticmethod
    @log_action("LOGIN")
    def login(username: str, password: str) -> User:
        """
        Выполняет вход пользователя.

        Args:
            username: Имя пользователя
            password: Пароль

        Returns:
            Объект пользователя

        Raises:
            UserNotFoundError: Если пользователь не найден
            AuthenticationError: Если неверный пароль
        """
        # Находим пользователя
        user_data = db.get_user_by_username(username)
        if not user_data:
            raise UserNotFoundError(username)

        # Создаем объект пользователя
        user = User.from_dict(user_data)

        # Проверяем пароль
        if not user.verify_password(password):
            raise AuthenticationError()

        return user

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> None:
        """
        Изменяет пароль пользователя.

        Args:
            user_id: ID пользователя
            old_password: Старый пароль
            new_password: Новый пароль

        Raises:
            UserNotFoundError: Если пользователь не найден
            AuthenticationError: Если старый пароль неверный
        """
        # Находим пользователя
        user_data = db.get_user_by_id(user_id)
        if not user_data:
            raise UserNotFoundError(f"ID={user_id}")

        user = User.from_dict(user_data)

        # Проверяем старый пароль
        if not user.verify_password(old_password):
            raise AuthenticationError("Неверный старый пароль")

        # Меняем пароль
        user.change_password(new_password)

        # Сохраняем изменения
        users = db.get_users()
        for i, u in enumerate(users):
            if u["user_id"] == user_id:
                users[i] = user.to_dict()
                break

        db.save_users(users)


class PortfolioUseCase:
    """Бизнес-логика для работы с портфелями."""

    @staticmethod
    def get_portfolio(user_id: int) -> Portfolio:
        """
        Получает портфель пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Объект портфеля

        Raises:
            PortfolioNotFoundError: Если портфель не найден
        """
        portfolio_data = db.get_portfolio_by_user_id(user_id)
        if not portfolio_data:
            raise PortfolioNotFoundError(user_id)

        return Portfolio.from_dict(portfolio_data)

    @staticmethod
    def save_portfolio(portfolio: Portfolio) -> None:
        """Сохраняет портфель."""
        portfolios = db.get_portfolios()

        # Ищем и обновляем существующий портфель
        found = False
        for i, p in enumerate(portfolios):
            if p["user_id"] == portfolio.user_id:
                portfolios[i] = portfolio.to_dict()
                found = True
                break

        # Если не нашли, добавляем новый
        if not found:
            portfolios.append(portfolio.to_dict())

        db.save_portfolios(portfolios)

    @staticmethod
    def get_wallet(user_id: int, currency_code: str) -> Wallet:
        """
        Получает кошелёк пользователя для указанной валюты.

        Args:
            user_id: ID пользователя
            currency_code: Код валюты

        Returns:
            Объект кошелька

        Raises:
            PortfolioNotFoundError: Если портфель не найден
        """
        portfolio = PortfolioUseCase.get_portfolio(user_id)

        wallet = portfolio.get_wallet(currency_code)
        if not wallet:
            # Создаем кошелёк если его нет
            wallet = portfolio.add_currency(currency_code)
            PortfolioUseCase.save_portfolio(portfolio)

        return wallet

    @staticmethod
    def get_total_value(
        user_id: int,
        base_currency: str = "USD"
    ) -> Tuple[float, Dict[str, float]]:
        """
        Рассчитывает общую стоимость портфеля.

        Args:
            user_id: ID пользователя
            base_currency: Базовая валюта

        Returns:
            Кортеж (общая стоимость, детали по валютам)
        """
        portfolio = PortfolioUseCase.get_portfolio(user_id)

        # Получаем актуальные курсы
        rates_cache = RatesUseCase.get_rates_cache()

        total = portfolio.get_total_value(base_currency, rates_cache)

        # Рассчитываем стоимость каждой валюты отдельно
        details = {}
        for currency_code, wallet in portfolio.wallets.items():
            if currency_code == base_currency:
                details[currency_code] = wallet.balance
            else:
                rate = None
                pair_key = f"{currency_code}_{base_currency}"
                if pair_key in rates_cache.get("pairs", {}):
                    rate = rates_cache["pairs"][pair_key].get("rate")

                if rate:
                    details[currency_code] = wallet.balance * rate
                else:
                    details[currency_code] = 0.0

        return total, details


class RatesUseCase:
    """Бизнес-логика для работы с курсами валют."""

    @staticmethod
    def get_rates_cache() -> Dict[str, Any]:
        """
        Получает кэш курсов валют.

        Returns:
            Словарь с курсами
        """
        return db.get_rates()

    @staticmethod
    def get_rate(from_currency: str, to_currency: str) -> Tuple[float, str]:
        """
        Получает актуальный курс между валютами.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта

        Returns:
            Кортеж (курс, время обновления)

        Raises:
            CurrencyNotFoundError: Если валюта не найдена
            ApiRequestError: Если курс недоступен
        """
        # Валидируем коды валют
        try:
            from_currency = validate_currency_code(from_currency)
            to_currency = validate_currency_code(to_currency)

            # Проверяем существование валют
            _ = get_currency(from_currency)
            _ = get_currency(to_currency)
        except ValueError as e:
            raise CurrencyNotFoundError(str(e)) from e
        except CurrencyNotFoundError as e:
            raise e

        if from_currency == to_currency:
            return 1.0, datetime.now().isoformat()

        # Получаем кэш курсов
        rates_cache = RatesUseCase.get_rates_cache()
        pairs = rates_cache.get("pairs", {})

        # Пытаемся найти прямой курс
        pair_key = f"{from_currency}_{to_currency}"
        if pair_key in pairs:
            pair_data = pairs[pair_key]
            rate = pair_data.get("rate")
            updated_at = pair_data.get("updated_at")

            if rate and updated_at:
                # Проверяем свежесть курса
                ttl = settings.get_rates_ttl()
                if is_rate_fresh(updated_at, ttl):
                    return rate, updated_at

        # Пытаемся найти обратный курс
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in pairs:
            pair_data = pairs[reverse_key]
            rate = pair_data.get("rate")
            updated_at = pair_data.get("updated_at")

            if rate and updated_at:
                # Проверяем свежесть курса
                ttl = settings.get_rates_ttl()
                if is_rate_fresh(updated_at, ttl):
                    return 1 / rate, updated_at

        # Если курс не найден или устарел
        raise ApiRequestError(
            f"Курс {from_currency}→{to_currency} недоступен. "
            f"Попробуйте обновить курсы командой 'update-rates'."
        )

    @staticmethod
    def update_rates_cache(rates_data: Dict[str, Any]) -> None:
        """
        Обновляет кэш курсов.

        Args:
            rates_data: Новые данные курсов
        """
        current_rates = db.get_rates()

        # Обновляем пары
        for pair_key, pair_data in rates_data.get("pairs", {}).items():
            current_rates.setdefault("pairs", {})[pair_key] = pair_data

        # Обновляем время последнего обновления
        current_rates["last_refresh"] = rates_data.get(
            "last_refresh",
            datetime.now().isoformat()
        )

        db.save_rates(current_rates)


class TradeUseCase:
    """Бизнес-логика для торговых операций."""

    @staticmethod
    @log_action("BUY", verbose=True)
    def buy(
        user_id: int,
        currency_code: str,
        amount: float,
        rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Покупает валюту.

        Args:
            user_id: ID пользователя
            currency_code: Код покупаемой валюты
            amount: Количество покупаемой валюты
            rate: Курс (если None, будет получен автоматически)

        Returns:
            Информация о операции

        Raises:
            CurrencyNotFoundError: Если валюта не найдена
            ValueError: Если сумма невалидна
            ApiRequestError: Если не удалось получить курс
        """
        # Валидация
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Получаем курс если не предоставлен
        if rate is None:
            try:
                rate, _ = RatesUseCase.get_rate(currency_code, "USD")
            except ApiRequestError as e:
                # Пробуем получить через USD кэш
                rates_cache = RatesUseCase.get_rates_cache()
                pairs = rates_cache.get("pairs", {})
                pair_key = f"{currency_code}_USD"

                if pair_key in pairs:
                    rate = pairs[pair_key].get("rate")

                if rate is None:
                    raise ApiRequestError(
                        f"Не удалось получить курс для {currency_code}. "
                        f"Попробуйте обновить курсы командой 'update-rates'."
                    ) from e

        # Получаем кошелёк
        portfolio = PortfolioUseCase.get_portfolio(user_id)

        # Проверяем наличие кошелька для валюты, если нет - создаем
        wallet = portfolio.get_wallet(currency_code)
        if not wallet:
            wallet = portfolio.add_currency(currency_code)

        # Пополняем кошелёк
        old_balance = wallet.balance
        wallet.deposit(amount)
        new_balance = wallet.balance

        # Сохраняем портфель
        PortfolioUseCase.save_portfolio(portfolio)

        # Рассчитываем оценочную стоимость
        estimated_cost = amount * rate if rate else 0.0

        return {
            "currency": currency_code,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "rate": rate,
            "estimated_cost_usd": estimated_cost,
            "success": True
        }

    @staticmethod
    @log_action("SELL", verbose=True)
    def sell(
        user_id: int,
        currency_code: str,
        amount: float,
        rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Продает валюту.

        Args:
            user_id: ID пользователя
            currency_code: Код продаваемой валюты
            amount: Количество продаваемой валюты
            rate: Курс (если None, будет получен автоматически)

        Returns:
            Информация о операции

        Raises:
            CurrencyNotFoundError: Если валюта не найдена
            ValueError: Если сумма невалидна
            InsufficientFundsError: Если недостаточно средств
            ApiRequestError: Если не удалось получить курс
        """
        # Валидация
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Получаем кошелёк
        portfolio = PortfolioUseCase.get_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)

        if not wallet:
            raise InsufficientFundsError(currency_code, 0.0, amount)

        # Проверяем баланс
        if wallet.balance < amount:
            raise InsufficientFundsError(
                currency_code,
                wallet.balance,
                amount
            )

        # Получаем курс если не предоставлен
        if rate is None:
            try:
                rate, _ = RatesUseCase.get_rate(currency_code, "USD")
            except ApiRequestError as e:
                # Пробуем получить через USD кэш
                rates_cache = RatesUseCase.get_rates_cache()
                pairs = rates_cache.get("pairs", {})
                pair_key = f"{currency_code}_USD"

                if pair_key in pairs:
                    rate = pairs[pair_key].get("rate")

                if rate is None:
                    raise ApiRequestError(
                        f"Не удалось получить курс для {currency_code}. "
                        f"Попробуйте обновить курсы командой 'update-rates'."
                    ) from e

        # Снимаем средства
        old_balance = wallet.balance
        wallet.withdraw(amount)
        new_balance = wallet.balance

        # Сохраняем портфель
        PortfolioUseCase.save_portfolio(portfolio)

        # Рассчитываем оценочную выручку
        estimated_revenue = amount * rate if rate else 0.0

        return {
            "currency": currency_code,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "rate": rate,
            "estimated_revenue_usd": estimated_revenue,
            "success": True
        }


# Создаем глобальные экземпляры для удобства
user_usecase = UserUseCase()
portfolio_usecase = PortfolioUseCase()
rates_usecase = RatesUseCase()
trade_usecase = TradeUseCase()
