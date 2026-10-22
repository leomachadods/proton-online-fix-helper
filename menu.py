#!/usr/bin/env python3
import sys

if sys.version_info < (3, 9):
    raise SystemExit('Requer Python 3.9 ou superior.')

from steamfix.app import main

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nCancelado.')
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Erro: {exc}')
