"""Ordenação e legibilidade dos dados exibidos pelo assistente."""
from pathlib import Path
import tempfile
import unittest

from steamfix.discovery import games, prefixes, prefix_proton


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'Steam'
        (self.root/'steamapps').mkdir(parents=True)

    def add_prefix(self, lib, appid, name=None):
        prefix = lib/'steamapps/compatdata'/appid
        (prefix/'pfx').mkdir(parents=True)
        (prefix/'pfx/user.reg').touch()
        if name:
            (lib/f'steamapps/appmanifest_{appid}.acf').write_text(
                f'"appid" "{appid}"\n"name" "{name}"\n"installdir" "{name}"')
        return prefix

    def test_game_prefix_is_first_with_clear_details(self):
        self.add_prefix(self.root, '1', 'Outro jogo')
        correct = self.add_prefix(self.root, '999', 'Jogo selecionado')
        (correct/'config_info').write_text('/tools/Proton Example/files/share/fonts/\n')
        result = prefixes({self.root}, '999', self.root)
        label, value = result[0]
        self.assertEqual(value, correct)
        for expected in ['RECOMENDADO', 'Jogo selecionado', '999', 'Proton Example', str(correct/'pfx')]:
            self.assertIn(expected, label)
        self.assertNotIn('RECOMENDADO', result[1][0])
        self.assertEqual(prefix_proton(correct), Path('/tools/Proton Example'))

    def test_same_id_in_another_library_is_not_first(self):
        external = Path(self.temp.name)/'AAA external'
        other = self.add_prefix(external, '999')
        selected = self.add_prefix(self.root, '999')
        result = prefixes({external, self.root}, '999', self.root)
        self.assertEqual(result[0][1], selected)
        self.assertEqual(result[1][1], other)
        self.assertNotIn('RECOMENDADO', result[1][0])

    def test_no_match_does_not_invent_recommendation(self):
        self.add_prefix(self.root, '1')
        result = prefixes({self.root}, '999', self.root)
        self.assertNotIn('RECOMENDADO', result[0][0])
        self.assertIn('Sem nome identificado', result[0][0])

    def test_steam_tools_are_not_listed_as_games(self):
        for appid, title in [('1', 'Proton Experimental'), ('2', 'Steamworks Common Redistributables'), ('3', 'Meu Jogo')]:
            folder = self.root/'steamapps/common'/title
            folder.mkdir(parents=True)
            (folder/'program.exe').touch()
            (self.root/f'steamapps/appmanifest_{appid}.acf').write_text(
                f'"appid" "{appid}"\n"name" "{title}"\n"installdir" "{title}"')
        items = games({self.root})
        self.assertEqual(len(items), 1)
        self.assertIn('Meu Jogo', items[0][0])
