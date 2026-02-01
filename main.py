import io
import sys

from valutatrade_hub.cli.interface import main as cli_main

# Принудительно UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    """Точка входа в приложение."""
    cli_main()

if __name__ == "__main__":
    main()
