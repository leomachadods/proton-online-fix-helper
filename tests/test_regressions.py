import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from steamfix import discovery, packages


class Regressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_config_save_replaces_whole_section(self):
        config = self.base/'games.conf'
        config.write_text('[other]\npath=/other\n\n[_game]\npath=/game\ncompatdata=1\n\n')
        code = f'''source "{ROOT}/lib/config.sh"
CONFIG_DIR="$TEST_DIR"; CONFIG_FILE="$TEST_DIR/games.conf"
GAME_DIR=/game; COMPAT_ID=2; APPID=""; WANT_DLLS=""; FAKE_APPID=""; REAL_APPID=""
ok() {{ :; }}
config_save && config_save
'''
        subprocess.run(['bash', '-uc', code], env={**os.environ, 'TEST_DIR': str(self.base)}, check=True)
        text = config.read_text()
        self.assertEqual(text.count('compatdata='), 1)
        self.assertIn('compatdata=2', text)
        self.assertIn('[other]\npath=/other', text)

    def fixture(self):
        root = self.base/'Steam'
        folder = root/'steamapps/common/Test Game'
        folder.mkdir(parents=True)
        (folder/'Test Game.exe').touch()
        (folder/'winmm.dll').touch()
        prefix = root/'steamapps/compatdata/123/pfx'
        prefix.mkdir(parents=True)
        (prefix/'user.reg').touch()
        proton = self.base/'Proton'
        proton.mkdir()
        exe = proton/'proton'
        exe.write_text('#!/bin/sh\necho invoked >> "$MARKER"\nexit 9\n')
        exe.chmod(0o755)
        return root, folder, proton

    def cli(self, command, *extra):
        root, folder, proton = self.fixture()
        env = {**os.environ, 'MARKER': str(self.base/'marker'), 'HOME': str(self.base)}
        result = subprocess.run(['bash', str(ROOT/'steam-dll-fix.sh'), command,
            '--path', str(folder), '--compatdata', '123', '--steam-root', str(root),
            '--proton', str(proton), '--no-config', *extra],
            capture_output=True, text=True, env=env)
        return result

    def test_launch_dry_run_does_not_execute_proton(self):
        result = self.cli('launch', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.base/'marker').exists())

    def test_apply_preview_does_not_execute_proton(self):
        result = self.cli('apply', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.base/'marker').exists())

    def test_winmm_fix_still_sets_native_then_builtin(self):
        code = f'''source "{ROOT}/lib/runtime.sh"
reg_set() {{ printf 'SET:%s:%s:%s:%s\\n' "$1" "$2" "$3" "$4"; }}
reg_load() {{ return 0; }}
reg_get() {{ printf 'n,b'; }}
ok() {{ :; }}
apply_dlls 123 'HKCU\\Software\\Wine\\DllOverrides' apply winmm
'''
        result = subprocess.run(['bash', '-uc', code], capture_output=True, text=True, check=True)
        self.assertIn('SET:123:HKCU\\Software\\Wine\\DllOverrides:winmm:n,b', result.stdout)

    def test_launch_returns_failure_when_apply_fails(self):
        result = self.cli('launch')
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_dll_name_is_rejected(self):
        result = self.cli('apply', '--dll', 'foo"=bar')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base/'marker').exists())

    def test_ini_preview_does_not_create_backup(self):
        ini = self.base/'OnlineFix.ini'
        ini.write_text('[Main]\nFakeAppId=480\n')
        code = f'''source "{ROOT}/lib/ini.sh"
DRY=1; FAKE_APPID=123; REAL_APPID=""
info() {{ :; }}
fix_onlinefix_ini "$TEST_DIR"
'''
        subprocess.run(['bash', '-uc', code], env={**os.environ, 'TEST_DIR': str(self.base)}, check=True)
        self.assertFalse((self.base/'OnlineFix.ini.bak').exists())
        self.assertIn('FakeAppId=480', ini.read_text())

    def test_import_rejects_destination_symlink(self):
        source, game = self.base/'source', self.base/'game'
        source.mkdir(); game.mkdir()
        (source/'winmm.dll').write_text('new')
        (game/'real.dll').write_text('old')
        (game/'winmm.dll').symlink_to(game/'real.dll')
        with self.assertRaises(ValueError):
            packages.plan(source, game)
        self.assertEqual((game/'real.dll').read_text(), 'old')

    def test_import_backup_and_rollback(self):
        source, game = self.base/'source', self.base/'game'
        source.mkdir(); game.mkdir()
        (source/'a.dll').write_text('new')
        (source/'b.dll').write_text('new b')
        (game/'a.dll').write_text('old')
        copy = packages.shutil.copy2
        def fail(src, dest, **kwargs):
            if Path(src) == source/'b.dll':
                raise OSError('simulated full disk')
            return copy(src, dest, **kwargs)
        with patch.object(packages.shutil, 'copy2', side_effect=fail):
            with self.assertRaises(OSError):
                packages.import_package(source, game)
        self.assertEqual((game/'a.dll').read_text(), 'old')
        self.assertFalse((game/'b.dll').exists())

    def test_import_success_keeps_backup(self):
        source, game = self.base/'source', self.base/'game'
        source.mkdir(); game.mkdir()
        (source/'a.dll').write_text('new')
        (game/'a.dll').write_text('old')
        backup = packages.import_package(source, game)
        self.assertEqual((game/'a.dll').read_text(), 'new')
        self.assertEqual((backup/'a.dll').read_text(), 'old')

    def test_discovery_rejects_manifest_traversal(self):
        root = self.base/'Steam'
        (root/'steamapps').mkdir(parents=True)
        (root/'steamapps/appmanifest_1.acf').write_text('"appid" "1"\n"installdir" "../../../outside"')
        self.assertEqual(discovery.games({root}), [])


if __name__ == '__main__':
    unittest.main()
