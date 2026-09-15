import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('common.paths', PROJECT_ROOT / 'common' / 'paths.py')
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)


class DataPathTest(unittest.TestCase):
    def test_defaults_to_the_working_directory(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DATA_DIR', None)
            self.assertEqual(paths.data_path('entries.json'), Path('.') / 'entries.json')

    def test_data_dir_is_used_and_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'state' / 'nested'
            with mock.patch.dict(os.environ, {'DATA_DIR': str(target)}):
                self.assertEqual(paths.data_path('entries.json'), target / 'entries.json')
                self.assertTrue(target.is_dir())


if __name__ == '__main__':
    unittest.main()
