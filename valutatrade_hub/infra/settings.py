"""
Singleton для загрузки конфигурации.
"""
import os
from typing import Any, Optional

import tomli


class SettingsLoader:
    """Singleton для загрузки настроек из pyproject.toml."""

    _instance: Optional['SettingsLoader'] = None
    _config: dict = {}

    def __new__(cls) -> 'SettingsLoader':
        """Создает единственный экземпляр SettingsLoader."""
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Загружает конфигурацию из pyproject.toml."""
        config_file = "pyproject.toml"

        if os.path.exists(config_file):
            try:
                with open(config_file, "rb") as f:
                    data = tomli.load(f)

                # Получаем секцию [tool.valutatrade] или используем значения по умолчанию
                valuta_config = data.get("tool", {}).get("valutatrade", {})

                self._config = {
                    "data_dir": valuta_config.get("data_dir", "data"),
                    "default_base_currency": valuta_config.get("default_base_currency", "USD"),
                    "rates_ttl_seconds": valuta_config.get("rates_ttl_seconds", 300),
                    "log_file": valuta_config.get("log_file", "logs/valutatrade.log"),
                    "parser_enabled": valuta_config.get("parser_enabled", True),
                    "parser_interval_minutes": valuta_config.get("parser_interval_minutes", 15),
                    "coingecko_timeout": valuta_config.get("coingecko_timeout", 10),
                    "exchangerate_timeout": valuta_config.get("exchangerate_timeout", 10),
                }

                # Загружаем API ключи из переменных окружения
                self._config["exchangerate_api_key"] = os.getenv(
                    "EXCHANGERATE_API_KEY",
                    valuta_config.get("exchangerate_api_key", "")
                )

            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
                self._set_defaults()
        else:
            self._set_defaults()

    def _set_defaults(self) -> None:
        """Устанавливает значения по умолчанию."""
        self._config = {
            "data_dir": "data",
            "default_base_currency": "USD",
            "rates_ttl_seconds": 300,  # 5 минут
            "log_file": "logs/valutatrade.log",
            "parser_enabled": True,
            "parser_interval_minutes": 15,
            "coingecko_timeout": 10,
            "exchangerate_timeout": 10,
            "exchangerate_api_key": "",
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение конфигурации.

        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию

        Returns:
            Значение конфигурации или default
        """
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перезагружает конфигурацию."""
        self._load_config()

    def get_data_path(self, filename: str) -> str:
        """
        Получает полный путь к файлу в data директории.

        Args:
            filename: Имя файла

        Returns:
            Полный путь
        """
        data_dir = self.get("data_dir", "data")
        return os.path.join(data_dir, filename)

    def get_log_file(self) -> str:
        """Получает путь к файлу логов."""
        return self.get("log_file", "logs/valutatrade.log")

    def get_rates_ttl(self) -> int:
        """Получает TTL кэша курсов в секундах."""
        return self.get("rates_ttl_seconds", 300)

    def get_default_base_currency(self) -> str:
        """Получает валюту по умолчанию для отображения."""
        return self.get("default_base_currency", "USD")


# Экспортируем глобальный экземпляр
settings = SettingsLoader()
