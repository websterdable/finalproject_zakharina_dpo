# valutatrade_hub/core/__init__.py
"""
Основная бизнес-логика приложения.
"""

from .currencies import (
    CryptoCurrency,
    Currency,
    FiatCurrency,
    get_all_currencies,
    get_currency,
)
from .exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    PortfolioNotFoundError,
    UserNotFoundError,
    ValutaTradeError,
)
from .models import Portfolio, User, Wallet
from .usecases import portfolio_usecase, rates_usecase, trade_usecase, user_usecase

__all__ = [
    'User', 'Wallet', 'Portfolio',
    'Currency', 'FiatCurrency', 'CryptoCurrency', 'get_currency', 'get_all_currencies',
    'ValutaTradeError', 'InsufficientFundsError', 'CurrencyNotFoundError',
    'ApiRequestError', 'UserNotFoundError', 'AuthenticationError', 'PortfolioNotFoundError',
    'user_usecase', 'portfolio_usecase', 'rates_usecase', 'trade_usecase'
]
