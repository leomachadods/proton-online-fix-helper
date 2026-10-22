"""O caminho principal não exige conhecer DLL overrides nem executar diagnóstico."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from steamfix import workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.options = ['--no-config']

    def test_main_has_separate_prepare_and_play_choices(self):
        self.assertEqual([v for _, v in workflow.MAIN_ACTIONS], ['play', 'prepare', 'advanced', 'exit'])

    def test_prepare_only_never_requests_launch(self):
        (self.folder/'winmm.dll').touch()
        with patch.object(workflow, 'choose', side_effect=['prepare', 'exit']), \
                patch.object(workflow, 'run_backend', return_value=0) as run:
            workflow.actions_menu(self.folder, Path('/prefix'), Path('/Proton'), self.options)
        run.assert_called_once_with('apply', self.options)

    def test_prepare_import_cancel_does_not_apply_or_launch(self):
        with patch.object(workflow, 'choose', return_value='import'), \
                patch.object(workflow, 'import_files', return_value=False), \
                patch.object(workflow, 'run_backend') as run:
            workflow.play(self.folder, self.options, start_game=False)
        run.assert_not_called()

    def test_play_uses_single_launch_without_technical_questions(self):
        (self.folder/'WINMM.DLL').touch()
        with patch.object(workflow, 'run_backend', return_value=0) as run, \
                patch.object(workflow, 'choose') as choose:
            workflow.play(self.folder, self.options)
        run.assert_called_once_with('launch', self.options)
        choose.assert_not_called()

    def test_missing_files_allow_return_without_launch(self):
        with patch.object(workflow, 'choose', return_value='back'), \
                patch.object(workflow, 'run_backend') as run:
            workflow.play(self.folder, self.options)
        run.assert_not_called()

    def test_canceled_import_does_not_open_game(self):
        with patch.object(workflow, 'choose', return_value='import'), \
                patch.object(workflow, 'import_files', return_value=False), \
                patch.object(workflow, 'run_backend') as run:
            workflow.play(self.folder, self.options)
        run.assert_not_called()

    def test_advanced_back_returns_to_main(self):
        with patch.object(workflow, 'choose', side_effect=['advanced', 'back', 'exit']), \
                patch.object(workflow, 'run_backend') as run:
            workflow.actions_menu(self.folder, Path('/prefix'), Path('/Proton'), self.options)
        run.assert_not_called()

    def test_preview_is_available_in_advanced_only(self):
        with patch.object(workflow, 'choose', side_effect=['preview', 'back']), \
                patch.object(workflow, 'run_backend', return_value=0) as run:
            workflow.advanced(self.folder, Path('/prefix'), Path('/Proton'), self.options)
        run.assert_called_once_with('apply', self.options + ['--dry-run'])
