#!/usr/bin/env python3
import sys
import argparse

if sys.version_info < (3, 9):
    raise SystemExit('Requer Python 3.9 ou superior.')

from steamfix.app import main

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Proton Online Fix Helper — interface de terminal')
    parser.add_argument('--plain', action='store_true', help='usar o menu numerado em vez da TUI')
    args = parser.parse_args()
    try:
        if args.plain:
            main()
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise SystemExit('A TUI requer um terminal interativo. Alternativa: ./steam-fix-menu.sh --plain')
            try:
                from steamfix.tui import run
            except ImportError:
                raise SystemExit('curses não está disponível. Use ./steam-fix-menu.sh --plain')
            import curses
            try:
                run(main)
            except curses.error:
                raise SystemExit('Não foi possível iniciar a TUI neste terminal. Use ./steam-fix-menu.sh --plain')
    except (KeyboardInterrupt, EOFError):
        print('\nCancelado.')
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Erro: {exc}')
