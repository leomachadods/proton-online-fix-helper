"""Patch de rede opt-in: leitura, edição segura e backup do localconfig.vdf."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from steamfix import netsock

ROOT = Path(__file__).resolve().parents[1]

VDF = '''"UserLocalConfigStore"
{
	"Software"
	{
		"Valve"
		{
			"Steam"
			{
				"apps"
				{
					"4210580"
					{
						"cloud"
						{
							"last_sync_state"		"synchronized"
						}
						"LaunchOptions"		"WINEDLLOVERRIDES=\\"winmm=n,b\\" %command%"
						"Playtime"		"73"
					}
					"480"
					{
						"LaunchOptions"		""
					}
				}
			}
		}
	}
}
'''


class NetsockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base/'Steam'
        (self.root/'config').mkdir(parents=True)
        (self.root/'config/loginusers.vdf').write_text(
            '"users"\n{\n'
            '\t"76561198990070648"\n\t{\n'
            '\t\t"AccountName"\t\t"mathi"\n'
            '\t\t"PersonaName"\t\t"Mathi"\n'
            '\t\t"MostRecent"\t\t"1"\n'
            '\t}\n}\n')
        self.config = self.root/'userdata/1029804920/config/localconfig.vdf'
        self.config.parent.mkdir(parents=True)
        self.config.write_text(VDF)
        self.patch = self.base/'SLSsteam/tools/netsock/netsock.so'
        self.patch.parent.mkdir(parents=True)
        self.patch.write_bytes(b'fake patch')

    def test_active_account_and_current_options(self):
        self.assertEqual(netsock.active_steam_id(self.root), '76561198990070648')
        path, value = netsock.current_launch_options(self.root, '4210580')
        self.assertEqual(path, self.config)
        self.assertEqual(value, 'WINEDLLOVERRIDES="winmm=n,b" %command%')

    def test_compose_is_idempotent_and_removes_cleanly(self):
        original = 'WINEDLLOVERRIDES="winmm=n,b" %command%'
        new = netsock.compose_launch_options(original, self.patch)
        self.assertIn('LD_AUDIT=', new)
        self.assertTrue(new.endswith('%command%'))
        self.assertEqual(netsock.compose_launch_options(new, self.patch), new)
        self.assertEqual(netsock.strip_launch_options(new, self.patch), original)

    def test_other_launch_arguments_are_preserved(self):
        original = 'WINEDLLOVERRIDES="winmm=n,b" %command% --foo "bar baz"'
        new = netsock.compose_launch_options(original, self.patch)
        self.assertIn('--foo "bar baz"', new)
        self.assertEqual(netsock.strip_launch_options(new, self.patch), original)

    def test_different_ld_audit_requires_force(self):
        current = 'LD_AUDIT="/old/netsock.so" %command%'
        with self.assertRaises(ValueError):
            netsock.compose_launch_options(current, self.patch)
        new = netsock.compose_launch_options(current, self.patch, force=True)
        self.assertIn('LD_AUDIT=', new)
        self.assertNotIn('/old/netsock.so', new)

    def test_path_with_spaces_is_quoted(self):
        patch = self.base/'com espaço/netsock.so'
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b'x')
        value = netsock.compose_launch_options('', patch)
        self.assertIn("LD_AUDIT='%s'" % patch, value)

    def test_apply_creates_backup_and_remove_restores(self):
        original = self.config.read_text()
        with patch.object(netsock, 'steam_running', return_value=False):
            result = netsock.apply(self.root, '4210580', patch=self.patch)
        self.assertTrue(result['changed'])
        self.assertIn('LD_AUDIT=', self.config.read_text())
        self.assertTrue(result['backup'].is_file())
        self.assertEqual(result['backup'].read_text(), original)
        with patch.object(netsock, 'steam_running', return_value=False):
            removed = netsock.remove(self.root, '4210580', patch=self.patch)
        self.assertTrue(removed['changed'])
        self.assertNotEqual(removed['backup'], result['backup'])
        self.assertTrue(removed['backup'].is_file())
        self.assertEqual(netsock.current_launch_options(self.root, '4210580')[1],
                         'WINEDLLOVERRIDES="winmm=n,b" %command%')

    def test_apply_refuses_steam_running_and_force_bypasses(self):
        with patch.object(netsock, 'steam_running', return_value=True):
            with self.assertRaises(ValueError):
                netsock.apply(self.root, '4210580', patch=self.patch)
            result = netsock.apply(self.root, '4210580', patch=self.patch, force=True)
        self.assertTrue(result['changed'])

    def test_dry_run_does_not_write(self):
        original = self.config.read_text()
        with patch.object(netsock, 'steam_running', return_value=False):
            result = netsock.apply(self.root, '4210580', patch=self.patch, dry_run=True)
        self.assertTrue(result.get('dry_run'))
        self.assertEqual(self.config.read_text(), original)
        self.assertIsNone(result['backup'])

    def test_symlink_config_is_refused(self):
        target = self.base/'real-localconfig.vdf'
        target.write_text(VDF)
        self.config.unlink()
        self.config.symlink_to(target)
        with patch.object(netsock, 'steam_running', return_value=False):
            with self.assertRaises(ValueError):
                netsock.apply(self.root, '4210580', patch=self.patch)
        self.assertNotIn('LD_AUDIT', target.read_text())

    def test_missing_launch_options_entry_is_inserted(self):
        text = VDF.replace('\t\t\t\t\t\t"LaunchOptions"\t\t"WINEDLLOVERRIDES=\\"winmm=n,b\\" %command%"\n', '')
        self.config.write_text(text)
        with patch.object(netsock, 'steam_running', return_value=False):
            netsock.apply(self.root, '4210580', patch=self.patch)
        _, value = netsock.current_launch_options(self.root, '4210580')
        self.assertIn('LD_AUDIT=', value)
        self.assertIn('"Playtime"', self.config.read_text())

    def test_active_account_is_preferred_when_both_have_the_app(self):
        other = self.root/'userdata/1/config/localconfig.vdf'
        other.parent.mkdir(parents=True)
        other.write_text(VDF)
        self.assertEqual(netsock.select_config(self.root, '4210580'), self.config)

    def test_missing_appid_is_reported(self):
        with self.assertRaises(ValueError):
            netsock.current_launch_options(self.root, '999')

    def test_diagnostics_finds_audit_log_and_player_log(self):
        game = self.root/'steamapps/common/Test Game'
        game.mkdir(parents=True)
        (self.root/'steamapps/appmanifest_4210580.acf').write_text(
            '"appid" "4210580"\n"name" "Test Game"\n"installdir" "Test Game"\n')
        (game/'audit_patch.log').write_text('[data] LD_AUDIT loaded, version 2\n')
        log = self.root/'steamapps/compatdata/4210580/pfx/drive_c/users/steamuser/AppData/LocalLow/Dev/Test/Player.log'
        log.parent.mkdir(parents=True)
        log.write_text('Steam API has been initialized with App ID: 4210580\n'
                       'Lobby created: Test\n'
                       'Connection was closed by peer, Internal error accepting connection.  '
                       'Cert is not authorized for appid 4210580, only 480\n')
        with patch.object(netsock, 'steam_running', return_value=False):
            info = netsock.diagnostics(self.root, '4210580', patch=str(self.patch))
        self.assertTrue(info['patch_exists'])
        self.assertEqual(info['player_log']['cert_errors'], 1)
        self.assertIn('only 480', info['player_log']['last_cert'])
        self.assertIn('LD_AUDIT loaded', '\n'.join(info['audit_log']['lines']))
        text = netsock.format_diagnostics(info)
        self.assertIn('LD_AUDIT', text)
        self.assertIn('Config:', text)

    def test_running_process_detection_uses_wine_path(self):
        game = self.root/'steamapps/common/Test Game'
        game.mkdir(parents=True)
        (self.root/'steamapps/appmanifest_4210580.acf').write_text(
            '"appid" "4210580"\n"name" "Test Game"\n"installdir" "Test Game"\n')
        proc = self.base/'proc'/'123'
        proc.mkdir(parents=True)
        (proc/'cmdline').write_bytes(
            b'S:\\steamapps\\common\\Test Game\\Test Game.exe\0-force-d3d11\0')
        (proc/'environ').write_bytes(b'LD_AUDIT=/tmp/netsock.so\0')
        with patch.object(netsock, 'steam_running', return_value=False):
            info = netsock.diagnostics(self.root, '4210580', patch=str(self.patch),
                                       proc_root=self.base/'proc')
        self.assertEqual(info['processes'][0]['pid'], '123')
        self.assertEqual(info['processes'][0]['ld_audit'], '/tmp/netsock.so')

    def test_cli_status_and_apply(self):
        env = {**os.environ, 'HOME': str(self.base)}
        status = subprocess.run(
            ['bash', str(ROOT/'steam-dll-fix.sh'), 'netsock', '--appid', '4210580',
             '--steam-root', str(self.root), '--patch', str(self.patch), '--status'],
            capture_output=True, text=True, env=env)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn('LD_AUDIT', status.stdout)
        applied = subprocess.run(
            ['bash', str(ROOT/'steam-dll-fix.sh'), 'netsock', '--appid', '4210580',
             '--steam-root', str(self.root), '--patch', str(self.patch),
             '--apply', '--force'],
            capture_output=True, text=True, env=env)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertIn('LD_AUDIT=', self.config.read_text())
        removed = subprocess.run(
            ['bash', str(ROOT/'steam-dll-fix.sh'), 'netsock', '--appid', '4210580',
             '--steam-root', str(self.root), '--patch', str(self.patch),
             '--remove', '--force'],
            capture_output=True, text=True, env=env)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertEqual(netsock.current_launch_options(self.root, '4210580')[1],
                         'WINEDLLOVERRIDES="winmm=n,b" %command%')


if __name__ == '__main__':
    unittest.main()
