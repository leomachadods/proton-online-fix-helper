"""Guardrails específicos do pacote público."""
from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_no_certificate_patch_integration_in_runtime(self):
        self.assertFalse((ROOT/'lib/netsock.sh').exists())
        for pattern in ('*.sh', 'lib/*.sh', 'steamfix/*.py'):
            for path in ROOT.glob(pattern):
                source = path.read_text()
                self.assertNotIn('netsock', source.casefold(), str(path))
                self.assertNotIn('LD_AUDIT', source, str(path))

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
