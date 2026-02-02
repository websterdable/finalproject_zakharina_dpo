# ValutaTrade Hub

Консольное приложение на Python для отслеживания и симуляции торговли валютами.  
Включает Core Service для управления пользователями и портфелями, а также Parser Service для получения актуальных курсов валют.

## Описание

ValutaTrade Hub - это комплексная платформа, которая позволяет пользователям:
- Регистрироваться и управлять виртуальным портфелем фиатных и криптовалют
- Совершать сделки по покупке/продаже валют
- Отслеживать актуальные курсы в реальном времени
- Использовать автоматическое обновление курсов через Parser Service

## Требования

- Python 3.10+
- Poetry 1.8.0+

### Дополнительные технические аспекты
- **PrettyTable** — красивый вывод таблиц
- **Requests** — HTTP-запросы к внешним API
- **Ruff** — линтинг и форматирование кода
- **JSON** — хранение данных (пользователи, портфели, курсы)
- **Tomli** — чтение конфигурации TOML (Python 3.10)

## Установка и запуск

```bash
# Клонирование репозитория
(ssh)
git clone git@github.com:websterdable/finalproject_zakharina_dpo.git
(https)
git clone https://github.com/websterdable/finalproject_zakharina_dpo.git
cd finalproject_zakharina_dpo

# Установка зависимостей
poetry install

# Создание необходимых файлов данных
mkdir -p data logs
echo "[]" > data/users.json
echo "[]" > data/portfolios.json
echo '{"pairs": {}, "last_refresh": null}' > data/rates.json
echo "[]" > data/exchange_rates.json

# Запуск приложения (покажет справку)
poetry run project

# Проверка качества кода
poetry run ruff check .
```
```
## Структура проекта

finalproject_zakharina_dpo/
├── data/                           # Данные приложения
│   ├── users.json                  # Пользователи
│   ├── portfolios.json             # Портфели и кошельки
│   ├── rates.json                  # Кэш курсов валют
│   └── exchange_rates.json         # История курсов (Parser Service)
├── logs/                           # Логи приложения
├── valutatrade_hub/                # Основной пакет
│   ├── core/                       # Бизнес-логика
│   │   ├── currencies.py           # Иерархия валют (Currency → Fiat/Crypto)
│   │   ├── exceptions.py           # Пользовательские исключения
│   │   ├── models.py               # Основные модели (User, Wallet, Portfolio)
│   │   ├── usecases.py             # Бизнес-логика операций
│   │   └── utils.py                # Вспомогательные функции
│   ├── infra/                      # Инфраструктура
│   │   ├── settings.py             # Конфигурация (Singleton)
│   │   └── database.py             # Управление JSON-хранилищем (Singleton)
│   ├── parser_service/             # Parser Service
│   │   ├── config.py               # Конфигурация парсера
│   │   ├── api_clients.py          # Клиенты внешних API (CoinGecko, ExchangeRate)
│   │   ├── updater.py              # Основной модуль обновления
│   │   ├── storage.py              # Операции с хранилищем
│   │   └── scheduler.py            # Планировщик обновлений
│   ├── cli/                        # Командный интерфейс
│   │   └── interface.py            # CLI команды
│   ├── logging_config.py           # Настройка логирования
│   └── decorators.py               # Декораторы (@log_action)
├── main.py                         # Точка входа
├── pyproject.toml                  # Конфигурация Poetry
├── Makefile                        # Автоматизация команд
├── README.md                       # Документация
└── .gitignore                      # Игнорируемые файлы
```
# CoinGecko API
В проекте реализована интеграция с CoinGecko API для получения актуальных курсов криптовалют.

Поддерживаемые криптовалюты через CoinGecko:
BTC (Bitcoin) - ID: "bitcoin"
ETH (Ethereum) - ID: "ethereum"
SOL (Solana) - ID: "solana"
BNB (Binance Coin) - ID: "binancecoin"
XRP (Ripple) - ID: "ripple"

## Архитектура Parser Service
Режимы работы:
1. Основной режим (по умолчанию):
- CoinGecko API - всегда активен для криптовалют (BTC, ETH, SOL, BNB, XRP)
- ExchangeRate-API - активен только при наличии API ключа для фиатных валют
- Если ключ ExchangeRate отсутствует, система работает только с криптовалютами

2.Мок-режим (только для тестирования):
- Активируется флагом --source mock или параметром use_mock=True
- Использует фиктивные данные всех валют
- Предназначен для тестирования без доступа к интернету

## Основные команды CLI
Регистрация и вход
```
poetry run project register --username alice --password 1234
poetry run project login --username alice --password 1234
```
Работа с портфелем
```
poetry run project show-portfolio [--base <валюта>]
poetry run project buy --currency <код> --amount <сумма>
poetry run project sell --currency <код> --amount <сумма>
```
Курсы валют
```
poetry run project get-rate --from <валюта> --to <валюта>
poetry run project update-rates [--source <источник>]
poetry run project show-rates [--currency <валюта>] [--top N]
```
Справка
```
poetry run project help
```

Полный рабочий цикл
```
#Очистить всё
rm -rf data/ logs/
mkdir -p data logs
echo "[]" > data/users.json
echo "[]" > data/portfolios.json
echo '{"pairs": {}, "last_refresh": null}' > data/rates.json
echo "[]" > data/exchange_rates.json

#демо
poetry run project help
poetry run project register --username teacher --password teacher123
poetry run project login --username teacher --password teacher123
poetry run project update-rates
poetry run project show-rates --top 3
poetry run project buy --currency BTC --amount 0.05
poetry run project show-portfolio
poetry run project logout
```
Пример вывода show-portfolio
```
Портфель пользователя 'investor' (база: USD):
+--------+----------+-----------------+-------+
| Валюта |   Баланс | Стоимость в USD |  Доля |
+--------+----------+-----------------+-------+
| BTC    |   0.0500 |     2966.86 USD | 91.7% |
| EUR    | 1000.0000 |     1078.60 USD |  8.3% |
+--------+----------+-----------------+-------+

Итого: 4045.46 USD
```
# Сборка пакета
poetry build

## Автор

Захарина Екатерина.

Запись с помощью Asciinema отсутствует.