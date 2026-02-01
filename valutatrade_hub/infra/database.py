"""
Singleton для управления JSON-хранилищем.
"""
import json
import os
import threading
from typing import Any, Dict, List, Optional

from ..infra.settings import settings


class DatabaseManager:
    """Singleton для работы с JSON-хранилищем."""

    _instance: Optional['DatabaseManager'] = None
    _lock = threading.RLock()

    def __new__(cls) -> 'DatabaseManager':
        """Создает единственный экземпляр DatabaseManager."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def _get_file_path(self, filename: str) -> str:
        """Получает полный путь к файлу."""
        return settings.get_data_path(filename)

    def _ensure_data_dir(self) -> None:
        """Создает директорию data, если её нет."""
        data_dir = settings.get("data_dir", "data")
        os.makedirs(data_dir, exist_ok=True)

    def read_json(self, filename: str, default: Any = None) -> Any:
        """
        Читает JSON файл.

        Args:
            filename: Имя файла
            default: Значение по умолчанию если файл не существует

        Returns:
            Данные из файла или default
        """
        filepath = self._get_file_path(filename)

        if not os.path.exists(filepath):
            return default if default is not None else []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка чтения файла {filename}: {e}")
            return default if default is not None else []

    def write_json(self, filename: str, data: Any) -> None:
        """
        Записывает данные в JSON файл.

        Args:
            filename: Имя файла
            data: Данные для записи
        """
        with self._lock:
            self._ensure_data_dir()
            filepath = self._get_file_path(filename)

            # Создаем временный файл для атомарной записи
            temp_filepath = f"{filepath}.tmp"

            try:
                with open(temp_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Переименовываем временный файл в целевой
                os.replace(temp_filepath, filepath)
            except IOError as e:
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                raise e

    def get_users(self) -> List[Dict[str, Any]]:
        """Получает список пользователей."""
        return self.read_json("users.json", [])

    def save_users(self, users: List[Dict[str, Any]]) -> None:
        """Сохраняет список пользователей."""
        self.write_json("users.json", users)

    def get_portfolios(self) -> List[Dict[str, Any]]:
        """Получает список портфелей."""
        return self.read_json("portfolios.json", [])

    def save_portfolios(self, portfolios: List[Dict[str, Any]]) -> None:
        """Сохраняет список портфелей."""
        self.write_json("portfolios.json", portfolios)

    def get_rates(self) -> Dict[str, Any]:
        """Получает кэш курсов валют."""
        return self.read_json("rates.json", {"pairs": {}, "last_refresh": None})

    def save_rates(self, rates: Dict[str, Any]) -> None:
        """Сохраняет кэш курсов валют."""
        self.write_json("rates.json", rates)

    def get_exchange_rates_history(self) -> List[Dict[str, Any]]:
        """Получает историю курсов."""
        return self.read_json("exchange_rates.json", [])

    def save_exchange_rates_history(self, history: List[Dict[str, Any]]) -> None:
        """Сохраняет историю курсов."""
        self.write_json("exchange_rates.json", history)

    def append_to_history(self, rate_record: Dict[str, Any]) -> None:
        """Добавляет запись в историю курсов."""
        history = self.get_exchange_rates_history()
        history.append(rate_record)

        # Ограничиваем размер истории (последние 1000 записей)
        if len(history) > 1000:
            history = history[-1000:]

        self.save_exchange_rates_history(history)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Находит пользователя по ID."""
        users = self.get_users()
        for user in users:
            if user["user_id"] == user_id:
                return user
        return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Находит пользователя по имени."""
        users = self.get_users()
        for user in users:
            if user["username"] == username:
                return user
        return None

    def get_portfolio_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Находит портфель по ID пользователя."""
        portfolios = self.get_portfolios()
        for portfolio in portfolios:
            if portfolio["user_id"] == user_id:
                return portfolio
        return None

    def get_next_user_id(self) -> int:
        """Генерирует следующий ID пользователя."""
        users = self.get_users()
        if not users:
            return 1

        max_id = max(user["user_id"] for user in users)
        return max_id + 1


# Экспортируем глобальный экземпляр
db = DatabaseManager()
