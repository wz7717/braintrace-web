"""One trusted frozen inference in a disposable process. No HTTP or user code execution."""
from pathlib import Path
import argparse
import json
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    # The parent attaches the process tree to its lifetime boundary before opening this gate.
    deadline = time.monotonic() + 15
    while not (work/'START').is_file():
        if time.monotonic() >= deadline:
            return 2
        time.sleep(.02)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import three_tier_backend as backend
        spec = json.loads((work/'request.json').read_text(encoding='utf-8'))
        data = (work/'input.bin').read_bytes()
        native = work/'native'; native.mkdir()
        os.environ['BRAINTRACE_TEMP_ROOT'] = str(native)
        if spec['species'] == 'human':
            program = 'BOTH' if len(spec['configurations']) == 2 else spec['configurations'][0]
            if sys.platform.startswith('linux'):
                from portability.human_linux import run_human
            else:
                run_human = backend.run_human
            result = run_human(data, spec['suffix'], spec['sample_id'], program)
        else:
            result = backend.run_macaque(data, spec['suffix'], spec['sample_id'], spec['configurations'])
        if spec['source'] == 'example':
            result['saved_output_comparison'] = backend.compare_example(result, spec['example_id'])
            if spec['species'] == 'macaque':
                backend.add_example_context(result, spec['example_id'])
        output = {'ok': True, 'result': result}
    except Exception:
        # Native diagnostics may contain uploaded identifiers or host paths; never export them.
        output = {'ok': False}
    temporary = work/'response.tmp'
    temporary.write_text(json.dumps(output, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporary.replace(work/'response.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
