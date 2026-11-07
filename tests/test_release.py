"""Guardrails específicos do pacote público."""
from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_network_patch_is_opt_in_and_not_automatic(self):
        # O patch de rede é uma ação explícita no submenu avançado. O backend
        # de launch não define LD_AUDIT por conta própria.
        self.assertFalse((ROOT/'lib/netsock.sh').exists())
        for path in ROOT.glob('lib/*.sh'):
            self.assertNotIn('LD_AUDIT', path.read_text(), str(path))
        self.assertTrue((ROOT/'steamfix/netsock.py').is_file())
        workflow = (ROOT/'steamfix/workflow.py').read_text()
        self.assertIn("'netsock'", workflow)
        self.assertIn('NETSOCK_ACTIONS', workflow)

    def test_removed_patch_flag_is_rejected(self):
        result = subprocess.run(['bash', str(ROOT/'steam-dll-fix.sh'), 'launch',
                                 '--netsock', '/nonexistent'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('opção desconhecida', result.stderr)

    def test_no_personal_absolute_paths_in_sources(self):
        for pattern in ('*.sh', 'lib/*.sh', 'steamfix/*.py'):
            for path in ROOT.glob(pattern):
                self.assertNotIn('/home/rei/', path.read_text(), str(path))

    def test_help_works_without_steam(self):
        result = subprocess.run(['bash', str(ROOT/'steam-dll-fix.sh'), '--help'],
                                env={**os.environ, 'STEAM_ROOT': '/nonexistent'},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Proton Online Fix Helper', result.stdout)
