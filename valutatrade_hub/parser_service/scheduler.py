"""
Планировщик периодического обновления курсов.
"""
import logging
import threading
import time
from typing import Optional

from .config import config
from .updater import RatesUpdater


class Scheduler:
    """Планировщик автоматического обновления курсов."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.updater = RatesUpdater()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self) -> None:
        """Запускает планировщик в фоновом потоке."""
        if self._is_running:
            self.logger.warning("Scheduler is already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._is_running = True

        self.logger.info(f"Scheduler started. Update interval: {config.UPDATE_INTERVAL} seconds")

    def stop(self) -> None:
        """Останавливает планировщик."""
        if not self._is_running:
            return

        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self._is_running = False
        self.logger.info("Scheduler stopped")

    def _run_loop(self) -> None:
        """Основной цикл планировщика."""
        self.logger.info("Scheduler loop started")

        while not self._stop_event.is_set():
            try:
                # Выполняем обновление
                self.logger.info("Scheduled update started")
                result = self.updater.run_update()

                if result.get("success"):
                    self.logger.info(f"Scheduled update completed: {result['total_rates']} rates")
                else:
                    self.logger.warning("Scheduled update completed with errors")

            except Exception as e:
                self.logger.error(f"Error in scheduled update: {e}")

            # Ждем указанный интервал или остановки
            for _ in range(config.UPDATE_INTERVAL):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        self.logger.info("Scheduler loop ended")

    def run_once(self) -> dict:
        """
        Выполняет единоразовое обновление.

        Returns:
            Результат обновления
        """
        return self.updater.run_update()

    def is_running(self) -> bool:
        """Проверяет, работает ли планировщик."""
        return self._is_running

    def get_status(self) -> dict:
        """
        Получает статус планировщика.

        Returns:
            Статус
        """
        update_status = self.updater.get_update_status()

        return {
            "is_running": self._is_running,
            "update_interval": config.UPDATE_INTERVAL,
            "last_update": update_status.get("last_refresh"),
            "rates_count": update_status.get("pairs_count", 0),
            "thread_alive": self._thread.is_alive() if self._thread else False
        }


# Глобальный экземпляр планировщика
scheduler = Scheduler()
