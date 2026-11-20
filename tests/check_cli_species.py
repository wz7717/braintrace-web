"""Exercise species selection through the installed single-sample CLI."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
MACAQUE_INPUT = ROOT / 'examples/three_tier/GSE128537/SINGLE_SAMPLE.npz'


class CliSpeciesChecks(unittest.TestCase):
    def setUp(self):
        self.work = Path(self.enterContext(TemporaryDirectory()))

    def cli(self, name, *options):
        out = self.work / name
        run = subprocess.run(
            [sys.executable, '-X', 'utf8', '-B', 'braintrace_cli.py', *options, '--out', str(out)],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        )
        return run, out

    def test_conflicts_stop_before_output_in_saved_and_live_modes(self):
        for requested, example, expected in [('human', 'GSE128537', 'macaque'), ('macaque', 'human', 'human')]:
            for mode, flags in [('saved', ['--saved']), ('live', [])]:
                with self.subTest(species=requested, example=example, mode=mode):
                    run, out = self.cli(f'{requested}-{mode}', '--species', requested, '--example', example, *flags)
                    self.assertEqual(run.returncode, 2, run.stderr)
                    message = run.stderr.splitlines()[-1]
                    for option in (f'--example {example}', f'--species {requested}', f'--species {expected}'):
                        self.assertIn(option, message)
                    self.assertFalse(out.exists())

    def assert_same_rankings(self, species, sample_id, *options):
        rankings = []
        for name, flags in [('implicit', []), ('explicit', ['--species', species])]:
            run, out = self.cli(name, *flags, *options)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads((out / 'result.json').read_text(encoding='utf-8'))
            self.assertEqual((result['species'], result['sample_id']), (species, sample_id))
            self.assertEqual(result['mode'], 'saved_example' if '--saved' in options else 'live_frozen_inference')
            if '--example' in options and '--saved' not in options:
                self.assertTrue(result['saved_output_comparison']['pass'])
            if species == 'human':
                items = result['predictions']
                self.assertEqual(set(items), {'RAW_FIXED', 'RANK_FIXED'})
            else:
                items = result['tiers']
                self.assertEqual(set(items), {'Network', 'Group', 'Exact'})
            self.assertTrue(all(item['ranking'] for item in items.values()))
            rankings.append({key: item['ranking'] for key, item in items.items()})
        self.assertEqual(rankings[0], rankings[1])

    def test_macaque_saved_example(self):
        self.assert_same_rankings('macaque', '10_10', '--example', 'GSE128537', '--saved')

    def test_human_saved_example(self):
        self.assert_same_rankings('human', 'GSM755211', '--example', 'human', '--program', 'BOTH', '--saved')

    def test_macaque_live_example(self):
        self.assert_same_rankings('macaque', 'LID_100660', '--example', 'GSE179328')

    def test_file_input_defaults_to_macaque(self):
        self.assert_same_rankings('macaque', 'cli_query', '--input', str(MACAQUE_INPUT), '--sample-id', 'cli_query')

    def test_file_input_honors_explicit_human_species(self):
        run, out = self.cli('human-input', '--species', 'human', '--input', str(MACAQUE_INPUT))
        self.assertEqual(run.returncode, 1, run.stderr)
        error = json.loads((out / 'error.json').read_text(encoding='utf-8'))
        self.assertIn('CEL/CEL.gz', error['error'])
        self.assertFalse((out / 'result.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
