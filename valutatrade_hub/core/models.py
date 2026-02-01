"""
Основные доменные модели: User, Wallet, Portfolio.
"""
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional

from .currencies import Currency, get_currency
from .exceptions import InsufficientFundsError


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime
    ):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Сеттер для имени пользователя с валидацией."""
        if not value or not isinstance(value, str) or len(value.strip()) == 0:
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Хэш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль для хэширования пароля."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации."""
        return self._registration_date

    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе (без пароля)."""
        return (
            f"Пользователь ID: {self.user_id}\n"
            f"Имя: {self.username}\n"
            f"Дата регистрации: {self.registration_date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Генерируем новую соль
        new_salt = secrets.token_hex(8)
        # Хэшируем пароль с солью
        new_hashed_password = self._hash_password(new_password, new_salt)

        self._hashed_password = new_hashed_password
        self._salt = new_salt

    def verify_password(self, password: str) -> bool:
        """Проверяет, соответствует ли пароль хэшу."""
        test_hash = self._hash_password(password, self.salt)
        return secrets.compare_digest(test_hash, self.hashed_password)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хэширует пароль с солью."""
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    @classmethod
    def create(cls, username: str, password: str) -> 'User':
        """Создает нового пользователя."""
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        salt = secrets.token_hex(8)
        hashed_password = cls._hash_password(password, salt)

        # user_id будет назначен позже, при сохранении
        return cls(
            user_id=0,  # временное значение
            username=username,
            hashed_password=hashed_password,
            salt=salt,
            registration_date=datetime.now()
        )

    def to_dict(self) -> dict:
        """Преобразует пользователя в словарь для JSON."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "salt": self.salt,
            "registration_date": self.registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создает пользователя из словаря."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"])
        )


class Wallet:
    """Кошелёк для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency_code = currency_code.upper()
        self._balance = 0.0
        self.balance = balance  # Используем сеттер для валидации

        # Получаем объект валюты для информации
        self._currency_obj: Optional[Currency] = None
        try:
            self._currency_obj = get_currency(currency_code)
        except Exception:
            pass  # Если валюта не найдена в реестре, объект останется None

    @property
    def currency_code(self) -> str:
        """Код валюты."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер баланса с валидацией."""
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    @property
    def currency_info(self) -> Optional[str]:
        """Информация о валюте."""
        if self._currency_obj:
            return self._currency_obj.get_display_info()
        return None

    def deposit(self, amount: float) -> None:
        """Пополняет баланс."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")

        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снимает средства с кошелька."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")

        if amount > self.balance:
            raise InsufficientFundsError(
                self.currency_code,
                self.balance,
                amount
            )

        self.balance -= amount

    def get_balance_info(self) -> str:
        """Возвращает информацию о балансе."""
        currency_info = self.currency_info or self.currency_code
        return f"{currency_info}: {self.balance:.4f}"

    def to_dict(self) -> dict:
        """Преобразует кошелёк в словарь для JSON."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        """Создает кошелёк из словаря."""
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )


class Portfolio:
    """Портфель пользователя (коллекция кошельков)."""

    def __init__(self, user_id: int, wallets: Optional[Dict[str, Wallet]] = None):
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = wallets or {}

    @property
    def user_id(self) -> int:
        """ID пользователя-владельца портфеля."""
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        """Копия словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавляет новый кошелёк для валюты.

        Args:
            currency_code: Код валюты

        Returns:
            Созданный или существующий кошелёк
        """
        currency_code = currency_code.upper()

        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code)

        return self._wallets[currency_code]

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает кошелёк по коду валюты."""
        return self._wallets.get(currency_code.upper())

    def get_total_value(self, base_currency: str = "USD", rates_cache: Optional[dict] = None) -> float:
        """
        Рассчитывает общую стоимость портфеля в базовой валюте.

        Args:
            base_currency: Базовая валюта для конвертации
            rates_cache: Кэш курсов валют

        Returns:
            Общая стоимость
        """
        total = 0.0

        for wallet in self._wallets.values():
            if wallet.currency_code == base_currency:
                total += wallet.balance
            else:
                # Пытаемся получить курс
                rate = self._get_exchange_rate(
                    wallet.currency_code,
                    base_currency,
                    rates_cache
                )
                if rate:
                    total += wallet.balance * rate

        return total

    def _get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rates_cache: Optional[dict]
    ) -> Optional[float]:
        """Получает курс обмена из кэша."""
        if not rates_cache:
            return None

        pair_key = f"{from_currency}_{to_currency}"
        if pair_key in rates_cache:
            return rates_cache[pair_key].get("rate")

        # Пробуем обратный курс
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in rates_cache:
            rate = rates_cache[reverse_key].get("rate")
            if rate:
                return 1 / rate

        return None

    def to_dict(self) -> dict:
        """Преобразует портфель в словарь для JSON."""
        return {
            "user_id": self.user_id,
            "wallets": {
                code: wallet.to_dict()
                for code, wallet in self._wallets.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        """Создает портфель из словаря."""
        wallets = {}
        for currency_code, wallet_data in data.get("wallets", {}).items():
            wallets[currency_code] = Wallet.from_dict(wallet_data)

        return cls(
            user_id=data["user_id"],
            wallets=wallets
        )
