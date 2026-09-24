"""Prove that the replay comparator detects a changed output."""
from pathlib import Path
import shutil
import tempfile
import unittest
from compare_versions import compare

ROOT = Path(__file__).resolve().parents[1]


class VersionParity(unittest.TestCase):
    def test_identical_package_matches(self):
        self.assertEqual(len(compare(ROOT, ROOT)), 3)

    def test_changed_score_export_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'changed'
            shutil.copytree(ROOT, changed, ignore=shutil.ignore_patterns('__pycache__'))
            script = changed / 'scripts/score.py'
            with script.open('a') as out:
                out.write("\nif __name__ == '__main__':\n import sys\n with open(sys.argv[sys.argv.index('--output')+1], 'a') as changed_output: changed_output.write('changed\\n')\n")
            with self.assertRaisesRegex(AssertionError, 'scores.csv'):
                compare(ROOT, changed)


if __name__ == '__main__':
    unittest.main()
