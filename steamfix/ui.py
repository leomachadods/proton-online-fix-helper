"""Entrada/saída interativa, sem dependência do código enviado por stdin."""
from pathlib import Path
import sys
import shutil
import textwrap

FRONTEND = None


class GoBack(Exception):
    """Volta uma etapa do assistente sem executar ações."""


def message(text, title='Informação'):
    if FRONTEND is not None:
        FRONTEND.text(title, text)
    else:
        print(text, flush=True)


def status(text):
    if FRONTEND is not None:
        FRONTEND.last_status = text
    else:
        print(text, flush=True)


def run_command(argv):
    if FRONTEND is not None:
        return FRONTEND.run_process(argv)
    import subprocess
    return subprocess.call(argv)


def ask(text):
    if FRONTEND is not None:
        return FRONTEND.prompt(text)
    if sys.stdin.isatty():
        try:
            return input(text).strip()
        except EOFError:
            raise SystemExit('Operação cancelada.')
    try:
        # TextIOWrapper em modo r+ exige seek em algumas versões do Python.
        # Terminais não são seekable: abrir leitura e escrita separadamente.
        with open('/dev/tty', 'r') as reader, open('/dev/tty', 'w') as writer:
            writer.write(text)
            writer.flush()
            answer = reader.readline()
    except OSError:
        raise SystemExit('Este menu requer um terminal. Use steam-dll-fix.sh para automação.')
    if not answer:
        raise SystemExit('Operação cancelada.')
    return answer.strip()


def choose(items, title, description=''):
    if not items:
        raise ValueError('Nenhuma opção disponível. Abra o jogo uma vez pelo Steam.')
    if FRONTEND is not None:
        return FRONTEND.choose(items, title, description)
    width = min(100, max(32, shutil.get_terminal_size((80, 24)).columns))
    print('\n' + '─' * width, flush=True)
    print(title, flush=True)
    print('─' * width, flush=True)
    if description:
        for line in description.splitlines():
            print(textwrap.fill(line, width=width), flush=True)
        print(flush=True)
    for i, (label, _) in enumerate(items, 1):
        lines = label.splitlines() or ['']
        for n, line in enumerate(lines):
            first = f'  [{i}] ' if n == 0 else '      '
            print(textwrap.fill(line, width=width, initial_indent=first,
                                subsequent_indent='      '), flush=True)
        print(flush=True)
    print('Digite o número da opção e pressione Enter. Enter vazio cancela.', flush=True)
    while True:
        answer = ask('Número (Enter cancela): ')
        if not answer:
            raise SystemExit(0)
        if answer.isdecimal() and 1 <= int(answer) <= len(items):
            return items[int(answer)-1][1]
        print('Escolha inválida.', flush=True)


def location(value):
    if not value.strip():
        raise ValueError('Caminho vazio.')
    return Path(value.strip().strip('"').strip("'")).expanduser().resolve()
