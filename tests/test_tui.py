"""Renderização e teclado sem depender de um terminal do usuário."""
import curses
from pathlib import Path
import unittest
from unittest.mock import patch
import os
import sys
import tempfile
import time

from steamfix import ui
from steamfix.tui import Screen, clean, fit, wrap


class Window:
    def __init__(self, keys, size=(24, 110)):
        self.keys = iter(keys)
        self.size = size
        self.drawn = []

    def getmaxyx(self):
        return self.size

    def erase(self):
        pass

    def addstr(self, y, x, text, attr=0):
        self.drawn.append((y, x, text))

    def move(self, y, x):
        pass

    def refresh(self):
        pass

    def getch(self):
        return next(self.keys)

    def get_wch(self):
        return next(self.keys)


def screen(keys, size=(24, 110)):
    instance = Screen.__new__(Screen)
    instance.screen = Window(keys, size)
    instance.last_status = 'Teste'
    instance.accent = curses.A_BOLD
    instance.muted = curses.A_DIM
    instance.selected = curses.A_REVERSE
    return instance


class TUITests(unittest.TestCase):
    def test_operation_records_log_and_preserves_failure_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = screen([])
            s.screen.timeout = lambda interval: None
            s.screen.getch = lambda: time.sleep(0.02)
            with patch.dict(os.environ, {'XDG_STATE_HOME': tmp}), patch.object(s, 'text') as result:
                rc = s.run_process([sys.executable, '-c', 'print("operation failed"); raise SystemExit(7)'])
            self.assertEqual(rc, 7)
            result.assert_called_once()
            logs = list(Path(tmp).rglob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].stat().st_mode & 0o777, 0o600)
            self.assertIn('operation failed', logs[0].read_text())

    def test_arrow_selection_returns_path_object(self):
        s = screen([curses.KEY_DOWN, 10])
        self.assertEqual(s.choose([('Primeiro', Path('/a')), ('Segundo', Path('/b'))], 'Jogos'), Path('/b'))

    def test_escape_goes_back_in_wizard(self):
        with self.assertRaises(ui.GoBack):
            screen([27]).choose([('Um', Path('/a'))], 'Prefixos')

    def test_escape_returns_back_in_advanced(self):
        self.assertEqual(screen([27]).choose([('Um', 'apply'), ('Voltar', 'back')], 'Avançado'), 'back')

    def test_escape_exits_main_menu(self):
        self.assertEqual(screen([27]).choose([('Jogar', 'play'), ('Sair', 'exit')], 'Jogo'), 'exit')

    def test_search_filters_and_enter_selects(self):
        s = screen([ord('/'), 'd', 'o', 'i', 's', '\n', 10])
        self.assertEqual(s.choose([('Um', 1), ('Dois', 2)], 'Jogos'), 2)

    def test_empty_search_has_no_invalid_selection(self):
        s = screen([ord('/'), 'x', '\n', 10, 27, 10])
        self.assertEqual(s.choose([('Um', 1)], 'Jogos'), 1)

    def test_compact_layout_and_details_scroll(self):
        s = screen([9, curses.KEY_DOWN, curses.KEY_NPAGE, 10], (18, 44))
        self.assertEqual(s.choose([('Um\n' + 'Caminho longo ' * 40, 1)], 'Opções'), 1)
        self.assertTrue(all(0 <= y < 18 and 0 <= x < 44 for y, x, _ in s.screen.drawn))

    def test_undersized_terminal_allows_safe_exit(self):
        with self.assertRaises(ui.GoBack):
            screen([27], (10, 30)).choose([('Um', 1)], 'Teste')

    def test_prompt_unicode_editing(self):
        s = screen(['á', 'b', curses.KEY_LEFT, curses.KEY_BACKSPACE, 'ç', '\n'])
        self.assertEqual(s.prompt('Resposta:'), 'çb')

    def test_prompt_escape_cancels(self):
        self.assertEqual(screen(['o', 'i', '\x1b']).prompt('Resposta:'), '')

    def test_word_wrap_handles_narrow_unicode(self):
        self.assertEqual(wrap('界', 1), ['?', ''])
        self.assertEqual(fit('a界b', 3), 'a界')
        self.assertEqual(clean('\x1b[31mhello\x1b[0m\x07'), 'hello')
