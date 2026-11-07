"""Interação real com pseudoterminal, sem Steam ou Proton."""
import os
from pathlib import Path
import pty
import subprocess
import sys
import unittest
from unittest.mock import patch

from steamfix import ui

ROOT = Path(__file__).resolve().parents[1]


class TerminalTests(unittest.TestCase):
    def test_choose_reads_number_from_terminal_stdin(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        process = subprocess.Popen(
            [sys.executable, '-c',
             'from steamfix.ui import choose; '
             'print("RESULT=" + choose([("Primeiro", "one"), ("Segundo", "two")], "Escolha"))'],
            cwd=ROOT, stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True)
        try:
            os.write(master, b'0\n2\n')
            out, err = process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        self.assertEqual(process.returncode, 0, out + err)
        self.assertIn('Escolha inválida.', out)
        self.assertIn('RESULT=two', out)

    def test_menu_without_terminal_reports_clear_error(self):
        result = subprocess.run(
            [sys.executable, '-c', 'from steamfix.ui import ask; ask("Escolha: ")'],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, start_new_session=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('terminal', result.stderr)

    def test_confirm_uses_yes_and_no_options(self):
        with patch.object(ui, 'choose', return_value=True) as choose:
            self.assertTrue(ui.confirm('Aplicar?', default=True))
        labels = [label.splitlines()[0] for label, _ in choose.call_args[0][0]]
        self.assertEqual(labels, ['Sim', 'Não'])

        with patch.object(ui, 'choose', return_value=False) as choose:
            self.assertFalse(ui.confirm('Remover?', default=False))
        labels = [label.splitlines()[0] for label, _ in choose.call_args[0][0]]
        self.assertEqual(labels, ['Não', 'Sim'])
