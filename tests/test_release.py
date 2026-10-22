"""Guardrails específicos do pacote público."""
from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_certificate_patch_is_disabled_by_default(self):
        # Executa só a inicialização do CLI, sem despacho nem Proton.
        source = (ROOT/'lib/cli.sh').read_text().split('while [[ $# -gt 0 ]]')[0]
        result = subprocess.run(['bash', '-uc', source + '\nprintf "%s" "$NO_NETSOCK"'],
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, '1')

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
