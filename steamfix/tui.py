"""Interface curses: apresentação e teclado; nenhuma decisão sobre Steam/DLLs."""
import curses
import datetime
import locale
import os
from pathlib import Path
import re
import subprocess
import time
import unicodedata
import uuid

from . import ui


def clean(text):
    """Não deixar saídas externas injetarem escapes no terminal."""
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(text))
    return ''.join(c for c in text if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127))


def cell_width(char):
    if unicodedata.combining(char) or unicodedata.category(char) in ('Cf', 'Mn', 'Me'):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1


def fit(text, width):
    result, used = '', 0
    for char in clean(text).replace('\n', ' ').replace('\t', '    '):
        size = cell_width(char)
        if used + size > width:
            break
        result += char
        used += size
    return result


def wrap(text, width):
    """Quebra por palavras e por largura visual para caminhos e Unicode."""
    width = max(1, width)
    result = []
    for original in clean(text).splitlines():
        line = ''
        for word in original.split():
            candidate = (line + ' ' + word).lstrip()
            if sum(map(cell_width, candidate)) <= width:
                line = candidate
                continue
            if line:
                result.append(line)
                line = ''
            while sum(map(cell_width, word)) > width:
                part = fit(word, width)
                if not part:
                    # Um glifo largo não cabe em uma coluna; consuma o glifo.
                    result.append('?')
                    word = word[1:]
                    continue
                result.append(part)
                word = word[len(part):]
            line = word
        result.append(line)
    return result or ['']


class Screen:
    def __init__(self, screen):
        self.screen = screen
        self.last_status = 'Nenhuma alteração feita.'
        self.accent = curses.A_BOLD
        self.muted = curses.A_DIM
        self.selected = curses.A_REVERSE | curses.A_BOLD
        self.screen.keypad(True)
        self.screen.timeout(-1)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            curses.init_pair(1, curses.COLOR_CYAN, background)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            self.accent = curses.color_pair(1) | curses.A_BOLD
            self.selected = curses.color_pair(2) | curses.A_BOLD

    def put(self, y, x, text, attr=0, width=None):
        rows, cols = self.screen.getmaxyx()
        if y < 0 or y >= rows or x < 0 or x >= cols:
            return
        width = min(cols - x - 1, width if width is not None else cols - x - 1)
        if width <= 0:
            return
        try:
            self.screen.addstr(y, x, fit(text, width), attr)
        except curses.error:
            pass  # Resize pode acontecer entre getmaxyx e addstr.

    def frame(self, title, footer):
        self.screen.erase()
        h, w = self.screen.getmaxyx()
        self.put(1, 2, 'PROTON ONLINE FIX HELPER', self.accent)
        self.put(2, 2, 'Steam + Proton  /  Assistente de configuração', self.muted)
        self.put(4, 2, title, curses.A_BOLD)
        self.put(h - 3, 2, self.last_status, self.muted)
        self.put(h - 2, 2, footer, self.accent)
        return h, w

    def panel(self, y, x, height, width, title):
        self.put(y, x, '+' + '-' * max(0, width - 2) + '+', self.muted)
        self.put(y, x + 2, ' ' + title + ' ', self.accent, max(0, width - 4))
        for row in range(y + 1, y + height - 1):
            self.put(row, x, '|', self.muted)
            self.put(row, x + width - 1, '|', self.muted)
        self.put(y + height - 1, x, '+' + '-' * max(0, width - 2) + '+', self.muted)

    def text(self, title, text):
        offset = 0
        while True:
            h, w = self.frame(title, '↑↓ Rolar   PgUp/PgDn Página   Enter/Esc Continuar')
            lines = wrap(text, max(1, w - 6))
            available = max(1, h - 10)
            offset = max(0, min(offset, max(0, len(lines) - available)))
            for i, line in enumerate(lines[offset:offset + available]):
                self.put(6 + i, 3, line)
            self.screen.refresh()
            key = self.screen.getch()
            if key in (10, 13, 27, curses.KEY_ENTER):
                return
            if key in (curses.KEY_DOWN, ord('j')):
                offset += 1
            elif key in (curses.KEY_UP, ord('k')):
                offset -= 1
            elif key == curses.KEY_NPAGE:
                offset += available
            elif key == curses.KEY_PPAGE:
                offset -= available

    def prompt(self, label):
        value, cursor = '', 0
        while True:
            h, w = self.frame('Preencher informação', 'Enter Confirmar   Esc Voltar   ←→ Mover cursor')
            for i, line in enumerate(wrap(label, max(1, w - 6))[:max(1, h - 12)]):
                self.put(6 + i, 3, line)
            hint = ('Caminhos com espaços são aceitos; não é preciso usar aspas.'
                    if any(token in label.casefold() for token in ('pasta', 'caminho'))
                    else 'Digite sua resposta e confirme com Enter. Esc cancela.')
            self.put(h - 7, 3, hint, self.muted)
            # Janela horizontal de texto baseada em células, não em bytes.
            start = 0
            while sum(map(cell_width, value[start:cursor])) > max(1, w - 9):
                start += 1
            self.put(h - 5, 3, '> ' + value[start:], self.selected, w - 6)
            try:
                curses.curs_set(1)
                self.screen.move(max(0, h - 5), min(w - 2, 5 + sum(map(cell_width, value[start:cursor]))))
            except curses.error:
                pass
            self.screen.refresh()
            try:
                key = self.screen.get_wch()
            except curses.error:
                continue
            if key in ('\n', '\r', curses.KEY_ENTER, '\x1b'):
                try:
                    curses.curs_set(0)
                except curses.error:
                    pass
                return '' if key == '\x1b' else value.strip()
            if key in (curses.KEY_BACKSPACE, '\x7f', '\b') and cursor:
                value, cursor = value[:cursor-1] + value[cursor:], cursor - 1
            elif key == curses.KEY_DC:
                value = value[:cursor] + value[cursor+1:]
            elif key == curses.KEY_LEFT:
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_RIGHT:
                cursor = min(len(value), cursor + 1)
            elif key == curses.KEY_HOME:
                cursor = 0
            elif key == curses.KEY_END:
                cursor = len(value)
            elif key == '\x15':
                value, cursor = '', 0
            elif isinstance(key, str) and key.isprintable():
                value = value[:cursor] + key + value[cursor:]
                cursor += len(key)

    def choose(self, items, title, description=''):
        selected, query, detail_offset = 0, '', 0
        focus_details = False
        while True:
            visible = [item for item in items if query.casefold() in item[0].casefold()]
            selected = max(0, min(selected, len(visible) - 1))
            h, w = self.frame(title, '↑↓ Mover  Enter OK  Esc Voltar  ? Ajuda')
            if w < 44 or h < 18:
                self.put(6, 2, 'Amplie o terminal (mínimo: 44 × 18).')
                self.put(8, 2, 'Esc: voltar sem alterar nada.')
                self.screen.refresh()
                if self.screen.getch() == 27:
                    raise ui.GoBack()
                continue
            self.put(5, 2, f'{len(visible)} opções' + (f'  /  Busca: {query}' if query else ''), self.muted)
            side_by_side = w >= 100
            list_width = max(30, (w - 6) // 2) if side_by_side else w - 4
            list_height = h - 10 if side_by_side else max(5, (h - 10) // 2)
            self.panel(6, 2, list_height, list_width, 'Escolha uma opção')
            page = max(1, (list_height - 2) // 2)
            top = max(0, selected - page + 1)
            for index, (label, _) in enumerate(visible[top:top + page], top):
                lines = label.splitlines()
                row = 7 + (index - top) * 2
                attr = self.selected if index == selected and not focus_details else curses.A_BOLD
                marker = '> ' if index == selected else '  '
                self.put(row, 4, marker + lines[0], attr, list_width - 4)
                if len(lines) > 1:
                    self.put(row + 1, 6, lines[1], self.muted, list_width - 6)
            if not visible:
                self.put(8, 5, 'Nenhuma opção encontrada.', self.muted)
            y = 6 if side_by_side else 6 + list_height
            x = list_width + 4 if side_by_side else 2
            detail_width = w - x - 2 if side_by_side else w - 4
            detail_height = h - 10 if side_by_side else h - y - 4
            self.panel(y, x, detail_height, detail_width, 'Detalhes' + (' • rolagem ativa' if focus_details else ''))
            label = visible[selected][0] if visible else ''
            details = label + ('\n\n' + description if description else '')
            lines = wrap(details, detail_width - 4)
            available = max(1, detail_height - 2)
            detail_offset = max(0, min(detail_offset, max(0, len(lines) - available)))
            for i, line in enumerate(lines[detail_offset:detail_offset + available]):
                self.put(y + 1 + i, x + 2, line, 0, detail_width - 4)
            self.screen.refresh()
            key = self.screen.getch()
            if key == ord('?'):
                self.text('Atalhos de teclado',
                          '↑ / ↓ ou j / k: selecionar uma opção\n'
                          'Enter: confirmar a opção destacada\n'
                          'Esc: voltar uma etapa; no menu principal, sair\n'
                          '/: buscar por nome, ID ou caminho\n'
                          'Esc após buscar: limpar a busca\n'
                          'Tab: alternar entre a lista e a rolagem dos detalhes\n'
                          'PgUp / PgDn: rolar uma página\n'
                          'Home / End: primeira ou última opção\n'
                          'Ctrl+C: sair da interface. Não encerra processos Proton já iniciados.\n\n'
                          'Em campos de texto: ← / →, Home, End, Backspace e Ctrl+U (limpar).\n'
                          'Se o terminal for estreito, os detalhes ficam abaixo da lista.')
            elif key == 27:
                if query:
                    query, selected = '', 0
                else:
                    for _, value in reversed(items):
                        if isinstance(value, str) and value in ('back', 'exit'):
                            return value
                    raise ui.GoBack()
            elif key in (10, 13, curses.KEY_ENTER) and visible:
                return visible[selected][1]
            elif key == 9:
                focus_details = not focus_details
            elif key == ord('/'):
                query = self.prompt('Buscar jogo, nome, caminho ou ID (Enter vazio limpa):')
                selected, detail_offset, focus_details = 0, 0, False
            elif key in (curses.KEY_DOWN, ord('j')):
                if focus_details:
                    detail_offset += 1
                else:
                    selected = min(len(visible) - 1, selected + 1)
                    detail_offset = 0
            elif key in (curses.KEY_UP, ord('k')):
                if focus_details:
                    detail_offset -= 1
                else:
                    selected = max(0, selected - 1)
                    detail_offset = 0
            elif key == curses.KEY_NPAGE:
                if focus_details:
                    detail_offset += available
                else:
                    selected = min(len(visible) - 1, selected + page)
            elif key == curses.KEY_PPAGE:
                if focus_details:
                    detail_offset -= available
                else:
                    selected = max(0, selected - page)
            elif key == curses.KEY_HOME:
                selected, detail_offset = 0, 0
            elif key == curses.KEY_END:
                selected, detail_offset = len(visible) - 1, 0

    def run_process(self, argv):
        base = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))
        logs = base/'proton-online-fix-helper/logs'
        logs.mkdir(parents=True, exist_ok=True)
        name = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.log'
        path = logs/name
        is_launch = len(argv) > 2 and argv[2] == 'launch'
        # Saída redirecionada evita corromper a tela curses. Não enviar entrada
        # do terminal para um processo filho enquanto a TUI está lendo teclas.
        with path.open('x', encoding='utf-8') as log:
            path.chmod(0o600)
            process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
            self.screen.timeout(120)
            try:
                while process.poll() is None:
                    h, w = self.frame('Preparando / executando o jogo' if is_launch else 'Processando configuração',
                                      'Aguarde. Feche o jogo para retornar.' if is_launch else 'Aguarde a operação terminar.')
                    self.put(7, 3, '|/-\\'[int(time.monotonic() * 6) % 4] + ' Operação em andamento…', self.accent)
                    self.put(9, 3, 'Log: ' + str(path), self.muted)
                    with path.open('rb') as reader:
                        reader.seek(max(0, path.stat().st_size - 4096))
                        tail = clean(reader.read().decode('utf-8', 'replace'))
                    lines = wrap(tail, max(1, w - 6))
                    for i, line in enumerate(lines[-max(1, h - 16):]):
                        self.put(12 + i, 3, line)
                    self.screen.refresh()
                    self.screen.getch()  # KEY_RESIZE é tratado na próxima renderização.
            finally:
                self.screen.timeout(-1)
        rc = process.returncode
        self.last_status = ('Concluído' if rc == 0 else f'Falhou (código {rc})') + ' • ' + str(path)
        self.text('Resultado da operação', self.last_status + '\n\n' +
                  path.read_text(errors='replace')[-20000:])
        return rc


def run(main):
    locale.setlocale(locale.LC_ALL, '')
    def session(screen):
        frontend = Screen(screen)
        ui.FRONTEND = frontend
        try:
            main()
        except ui.GoBack:
            pass
        except (OSError, ValueError) as exc:
            frontend.text('Não foi possível continuar', str(exc))
        finally:
            ui.FRONTEND = None
    return curses.wrapper(session)
