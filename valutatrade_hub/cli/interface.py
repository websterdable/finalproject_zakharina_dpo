"""
Командный интерфейс (CLI) для приложения.
"""
import argparse
import sys
from typing import Optional

from prettytable import PrettyTable

from ..core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    UserNotFoundError,
)
from ..core.models import User
from ..core.usecases import (
    portfolio_usecase,
    rates_usecase,
    trade_usecase,
    user_usecase,
)
from ..infra.settings import settings
from ..logging_config import setup_logging
from ..parser_service.scheduler import scheduler
from ..parser_service.updater import RatesUpdater


class CLI:
    """Основной класс командного интерфейса."""

    def __init__(self):
        self.current_user: Optional[User] = None
        self.logger = None
        self.setup_logging()

    def setup_logging(self):
        """Настраивает логирование."""
        log_file = settings.get_log_file()
        setup_logging(log_file)
        import logging
        self.logger = logging.getLogger(__name__)

    def run(self):
        """Запускает CLI."""
        parser = argparse.ArgumentParser(
            description='ValutaTrade Hub - Валютный кошелек с Parser Service',
            add_help=False
        )

        # Основные команды
        subparsers = parser.add_subparsers(dest='command', help='Команды')

        # Регистрация
        register_parser = subparsers.add_parser('register', help='Регистрация нового пользователя')
        register_parser.add_argument('--username', required=True, help='Имя пользователя')
        register_parser.add_argument('--password', required=True, help='Пароль')

        # Вход
        login_parser = subparsers.add_parser('login', help='Вход в систему')
        login_parser.add_argument('--username', required=True, help='Имя пользователя')
        login_parser.add_argument('--password', required=True, help='Пароль')

        # Показать портфель
        portfolio_parser = subparsers.add_parser('show-portfolio', help='Показать портфель')
        portfolio_parser.add_argument('--base', default='USD', help='Базовая валюта (по умолчанию: USD)')

        # Купить валюту
        buy_parser = subparsers.add_parser('buy', help='Купить валюту')
        buy_parser.add_argument('--currency', required=True, help='Код покупаемой валюты (например, BTC)')
        buy_parser.add_argument('--amount', type=float, required=True, help='Количество покупаемой валюты')

        # Продать валюту
        sell_parser = subparsers.add_parser('sell', help='Продать валюту')
        sell_parser.add_argument('--currency', required=True, help='Код продаваемой валюты')
        sell_parser.add_argument('--amount', type=float, required=True, help='Количество продаваемой валюты')

        # Получить курс
        rate_parser = subparsers.add_parser('get-rate', help='Получить курс валюты')
        rate_parser.add_argument('--from', dest='from_currency', required=True, help='Исходная валюта')
        rate_parser.add_argument('--to', dest='to_currency', required=True, help='Целевая валюта')

        # Обновить курсы
        update_parser = subparsers.add_parser('update-rates', help='Обновить курсы валют')
        update_parser.add_argument('--source', choices=['coingecko', 'exchangerate', 'mock'],
                                 help='Обновить только из указанного источника')

        # Показать курсы
        show_rates_parser = subparsers.add_parser('show-rates', help='Показать курсы из кэша')
        show_rates_parser.add_argument('--currency', help='Показать курс только для указанной валюты')
        show_rates_parser.add_argument('--top', type=int, help='Показать N самых дорогих криптовалют')
        show_rates_parser.add_argument('--base', default='USD', help='Базовая валюта для отображения')

        # Статус парсера
        subparsers.add_parser('parser-status', help='Показать статус Parser Service')

        # Запустить планировщик
        subparsers.add_parser('start-parser', help='Запустить автоматическое обновление курсов')

        # Остановить планировщик
        subparsers.add_parser('stop-parser', help='Остановить автоматическое обновление курсов')

        # Выход
        subparsers.add_parser('logout', help='Выйти из системы')

        # Помощь
        subparsers.add_parser('help', help='Показать справку')

        # Если аргументов нет, показываем справку
        if len(sys.argv) == 1:
            self.print_help()
            return

        try:
            args = parser.parse_args()
            self.handle_command(args)
        except SystemExit:
            # argparse выходит с SystemExit при --help
            pass
        except Exception as e:
            print(f"Ошибка: {e}")
            self.logger.error(f"CLI error: {e}")

    def handle_command(self, args):
        """Обрабатывает команду."""
        command = args.command

        if command == 'register':
            self.command_register(args)
        elif command == 'login':
            self.command_login(args)
        elif command == 'show-portfolio':
            self.command_show_portfolio(args)
        elif command == 'buy':
            self.command_buy(args)
        elif command == 'sell':
            self.command_sell(args)
        elif command == 'get-rate':
            self.command_get_rate(args)
        elif command == 'update-rates':
            self.command_update_rates(args)
        elif command == 'show-rates':
            self.command_show_rates(args)
        elif command == 'parser-status':
            self.command_parser_status()
        elif command == 'start-parser':
            self.command_start_parser()
        elif command == 'stop-parser':
            self.command_stop_parser()
        elif command == 'logout':
            self.command_logout()
        elif command == 'help':
            self.print_help()
        else:
            print(f"Неизвестная команда: {command}")
            self.print_help()

    def check_auth(self) -> bool:
        """Проверяет, авторизован ли пользователь."""
        if not self.current_user:
            print("Сначала выполните login")
            return False
        return True

    def command_register(self, args):
        """Команда регистрации."""
        try:
            user = user_usecase.register(args.username, args.password)
            print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
                  f"Войдите: login --username {args.username} --password ****")
        except ValueError as e:
            print(f"Ошибка регистрации: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            self.logger.error(f"Register error: {e}")

    def command_login(self, args):
        """Команда входа."""
        try:
            self.current_user = user_usecase.login(args.username, args.password)
            print(f"Вы вошли как '{self.current_user.username}'")
        except UserNotFoundError:
            print(f"Пользователь '{args.username}' не найден")
        except AuthenticationError:
            print("Неверный пароль")
        except Exception as e:
            print(f"Ошибка входа: {e}")
            self.logger.error(f"Login error: {e}")

    def command_show_portfolio(self, args):
        """Команда показа портфеля."""
        if not self.check_auth():
            return

        try:
            total_value, details = portfolio_usecase.get_total_value(
                self.current_user.user_id,
                args.base
            )

            if not details:
                print("Ваш портфель пуст")
                return

            table = PrettyTable()
            table.field_names = ["Валюта", "Баланс", f"Стоимость в {args.base}", "Доля"]
            table.align = "r"
            table.align["Валюта"] = "l"

            for currency, value in details.items():
                if currency == args.base:
                    balance = value
                    converted = value
                else:
                    # Нужно получить баланс из портфеля
                    portfolio = portfolio_usecase.get_portfolio(self.current_user.user_id)
                    wallet = portfolio.get_wallet(currency)
                    balance = wallet.balance if wallet else 0
                    converted = value

                percentage = (converted / total_value * 100) if total_value > 0 else 0

                table.add_row([
                    currency,
                    f"{balance:.4f}",
                    f"{converted:.2f} {args.base}",
                    f"{percentage:.1f}%"
                ])

            print(f"Портфель пользователя '{self.current_user.username}' (база: {args.base}):")
            print(table)
            print(f"\nИтого: {total_value:.2f} {args.base}")

        except Exception as e:
            print(f"Ошибка при получении портфеля: {e}")
            self.logger.error(f"Show portfolio error: {e}")

    def command_buy(self, args):
        """Команда покупки валюты."""
        if not self.check_auth():
            return

        try:
            result = trade_usecase.buy(
                self.current_user.user_id,
                args.currency,
                args.amount
            )

            print(f"Покупка выполнена: {args.amount:.4f} {args.currency}")

            if result.get('rate'):
                print(f"Курс: {result['rate']:.2f} USD/{args.currency}")

            if result.get('estimated_cost_usd'):
                print(f"Оценочная стоимость покупки: {result['estimated_cost_usd']:.2f} USD")

            print("Изменения в портфеле:")
            print(f"  - {args.currency}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}")

        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Проверьте код валюты или выполните 'show-rates' для списка доступных валют")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
        except Exception as e:
            print(f"Ошибка при покупке: {e}")
            self.logger.error(f"Buy error: {e}")

    def command_sell(self, args):
        """Команда продажи валюты."""
        if not self.check_auth():
            return

        try:
            result = trade_usecase.sell(
                self.current_user.user_id,
                args.currency,
                args.amount
            )

            print(f"Продажа выполнена: {args.amount:.4f} {args.currency}")

            if result.get('rate'):
                print(f"Курс: {result['rate']:.2f} USD/{args.currency}")

            if result.get('estimated_revenue_usd'):
                print(f"Оценочная выручка: {result['estimated_revenue_usd']:.2f} USD")

            print("Изменения в портфеле:")
            print(f"  - {args.currency}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}")

        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("У вас нет кошелька для этой валюты")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
        except Exception as e:
            print(f"Ошибка при продаже: {e}")
            self.logger.error(f"Sell error: {e}")

    def command_get_rate(self, args):
        """Команда получения курса."""
        try:
            rate, updated_at = rates_usecase.get_rate(args.from_currency, args.to_currency)

            # Форматируем время
            from datetime import datetime
            dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')

            print(f"Курс {args.from_currency}→{args.to_currency}: {rate:.6f}")
            print(f"Обратный курс {args.to_currency}→{args.from_currency}: {1/rate:.6f}")
            print(f"Обновлено: {time_str}")

        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Проверьте коды валют. Доступные валюты:")
            # Здесь можно добавить вывод списка доступных валют
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Попробуйте обновить курсы командой 'update-rates'")
        except Exception as e:
            print(f"Ошибка при получении курса: {e}")
            self.logger.error(f"Get rate error: {e}")

    def command_update_rates(self, args):
        """Команда обновления курсов."""
        try:
            updater = RatesUpdater(use_mock=(args.source == 'mock'))
            result = updater.run_update(args.source)

            if result.get('success'):
                print("Обновление успешно выполнено")
                print(f"Обновлено курсов: {result['total_rates']}")
                print(f"Время: {result['timestamp']}")

                for success in result['success']:
                    print(f"  - {success['source']}: {success['rates_count']} курсов "
                          f"({success['fetch_time_ms']}ms)")
            else:
                print("Обновление завершено с ошибками")

            if result.get('failed'):
                print("Ошибки:")
                for failure in result['failed']:
                    print(f"  - {failure['source']}: {failure['reason']}")

        except Exception as e:
            print(f"Ошибка при обновлении курсов: {e}")
            self.logger.error(f"Update rates error: {e}")

    def command_show_rates(self, args):
        """Команда показа курсов из кэша."""
        try:
            rates_cache = rates_usecase.get_rates_cache()
            pairs = rates_cache.get('pairs', {})

            if not pairs:
                print("Кэш курсов пуст. Выполните 'update-rates' для загрузки данных.")
                return

            # Фильтруем по валюте если указана
            filtered_pairs = {}
            if args.currency:
                currency = args.currency.upper()
                for pair_key, data in pairs.items():
                    if pair_key.startswith(f"{currency}_") or pair_key.endswith(f"_{currency}"):
                        filtered_pairs[pair_key] = data
            else:
                filtered_pairs = pairs

            if not filtered_pairs:
                print(f"Курсы для валюты '{args.currency}' не найдены в кэше")
                return

            # Сортируем
            sorted_pairs = sorted(
                filtered_pairs.items(),
                key=lambda x: x[1].get('rate', 0),
                reverse=True
            )

            # Ограничиваем если указан --top
            if args.top:
                sorted_pairs = sorted_pairs[:args.top]

            # Создаем таблицу
            table = PrettyTable()
            table.field_names = ["Пара", "Курс", "Обновлено", "Источник"]
            table.align = "r"
            table.align["Пара"] = "l"
            table.align["Источник"] = "l"

            for pair_key, data in sorted_pairs:
                rate = data.get('rate', 0)
                updated = data.get('updated_at', '')
                source = data.get('source', '')

                # Форматируем время
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except Exception:
                    time_str = updated

                table.add_row([pair_key, f"{rate:.6f}", time_str, source])

            last_refresh = rates_cache.get('last_refresh', '')
            if last_refresh:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
                    refresh_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    refresh_str = last_refresh

                print(f"Курсы из кэша (обновлено: {refresh_str}):")
            else:
                print("Курсы из кэша:")

            print(table)
            print(f"\nВсего пар: {len(filtered_pairs)}")

        except Exception as e:
            print(f"Ошибка при отображении курсов: {e}")
            self.logger.error(f"Show rates error: {e}")

    def command_parser_status(self):
        """Команда показа статуса парсера."""
        status = scheduler.get_status()

        print("Статус Parser Service:")
        print(f"  Работает: {'Да' if status['is_running'] else 'Нет'}")
        print(f"  Интервал обновления: {status['update_interval']} сек")
        print(f"  Последнее обновление: {status['last_update'] or 'Никогда'}")
        print(f"  Курсов в кэше: {status['rates_count']}")
        print(f"  Поток жив: {'Да' if status['thread_alive'] else 'Нет'}")

    def command_start_parser(self):
        """Команда запуска планировщика."""
        if scheduler.is_running():
            print("Parser Service уже запущен")
        else:
            scheduler.start()
            print("Parser Service запущен")

    def command_stop_parser(self):
        """Команда остановки планировщика."""
        if not scheduler.is_running():
            print("Parser Service не запущен")
        else:
            scheduler.stop()
            print("Parser Service остановлен")

    def command_logout(self):
        """Команда выхода."""
        if self.current_user:
            print(f"Вы вышли из системы (пользователь: {self.current_user.username})")
            self.current_user = None
        else:
            print("Вы не вошли в систему")

    def print_help(self):
        """Выводит справку."""
        help_text = """
ValutaTrade Hub - Валютный кошелек с Parser Service

Основные команды:

  Регистрация и вход:
    register --username <name> --password <pass>   Зарегистрироваться
    login --username <name> --password <pass>      Войти в систему
    logout                                         Выйти из системы

  Работа с портфелем:
    show-portfolio [--base <валюта>]               Показать портфель
    buy --currency <код> --amount <сумма>          Купить валюту
    sell --currency <код> --amount <сумма>         Продать валюту

  Курсы валют:
    get-rate --from <валюта> --to <валюта>         Получить курс
    update-rates [--source <источник>]             Обновить курсы валют
    show-rates [--currency <валюта>] [--top N]     Показать курсы из кэша

  Parser Service:
    parser-status                                  Статус Parser Service
    start-parser                                   Запустить автообновление
    stop-parser                                    Остановить автообновление

  Справка:
    help                                           Показать эту справку

Примеры:
  register --username alice --password 1234
  login --username alice --password 1234
  buy --currency BTC --amount 0.05
  show-portfolio --base USD
  update-rates
  get-rate --from USD --to BTC
        """
        print(help_text)


def main():
    """Точка входа CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
