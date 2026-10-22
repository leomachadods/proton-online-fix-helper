"""Smoke test da TUI real em PTY; todos os jogos e prefixos são fictícios."""
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FullTerminalTest(unittest.TestCase):
    def test_wizard_preview_back_resize_and_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            steam = base/'Steam'
            game = steam/'steamapps/common/Jogo Teste'
            game.mkdir(parents=True)
            (game/'Jogo Teste.exe').touch()
            (game/'winmm.dll').touch()
            (steam/'steamapps/appmanifest_999.acf').write_text(
                '"appid" "999"\n"name" "Jogo Teste"\n"installdir" "Jogo Teste"')
            prefix = steam/'steamapps/compatdata/999'
            (prefix/'pfx').mkdir(parents=True)
            (prefix/'pfx/user.reg').touch()
            proton = steam/'steamapps/common/Proton Teste'
            proton.mkdir()
            binary = proton/'proton'
            marker = base/'proton-invocado'
            binary.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 9\n')
            binary.chmod(0o755)
            (prefix/'config_info').write_text(str(proton) + '/files/share/fonts/\n')
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 110, 0, 0))
            env = {**os.environ, 'HOME': tmp, 'STEAM_ROOT': str(steam), 'TERM': 'xterm-256color',
                   'XDG_STATE_HOME': str(base/'state')}
            process = subprocess.Popen([sys.executable, str(ROOT/'menu.py')], cwd=ROOT,
                                       env=env, stdin=slave, stdout=slave, stderr=slave,
                                       start_new_session=True)
            transcript = bytearray()

            def wait_for(text):
                received = bytearray()
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError:
                            break
                        received.extend(chunk)
                        transcript.extend(chunk)
                        if text.encode() in received:
                            return
                    if process.poll() is not None:
                        break
                self.fail(f'TUI não mostrou {text!r}; saída: {transcript.decode(errors="replace")[-6000:]}')

            def key(value):
                os.write(master, value)

            try:
                wait_for('1/3')
                key(b'\n')
                wait_for('2/3')
                key(b'\n')
                wait_for('3/3')
                key(b'\x1b')  # Retorna do Proton para o prefixo.
                wait_for('2/3')
                key(b'\n')
                wait_for('3/3')
                key(b'\n')
                wait_for('Preparar e jogar')
                key(b'jj\n')
                wait_for('Configurar sem abrir')
                key(b'jj\n')  # Pré-visualização: sem executar o falso Proton.
                wait_for('Override proposto')
                key(b'\n')
                wait_for('Configurar sem abrir')
                # Redimensiona e testa retorno em layout compacto.
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 22, 70, 0, 0))
                os.kill(process.pid, signal.SIGWINCH)
                key(b'\x1b')
                wait_for('Preparar e jogar')
                key(b'\x1b')
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertFalse(marker.exists(), 'A pré-visualização executou o Proton!')
                self.assertIn(b'RECOMENDADO', transcript)
                self.assertNotIn(b'Traceback', transcript)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
