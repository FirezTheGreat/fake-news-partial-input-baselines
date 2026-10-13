"""Run the whole pipeline, or chosen steps.

    run              all steps, 0 to 7 (0 fetches and verifies the data)
    run 2            only step 2
    run 3 7          steps 3 and 7
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "scripts"
STEPS = {
    "0": "00_get_data.py",
    "1": "01_baseline.py",
    "2": "02_partial_input.py",
    "3": "03_stripped.py",
    "4": "04_cross_corpus.py",
    "5": "05_more_probes.py",
    "6": "06_confounds.py",
    "7": "07_figures.py",
}


def main():
    chosen = sys.argv[1:] or list(STEPS)
    unknown = [s for s in chosen if s not in STEPS]
    if unknown:
        sys.exit(f"unknown step(s): {', '.join(unknown)}. Choose from {', '.join(STEPS)}.")

    for step in chosen:
        script = STEPS[step]
        print(f"\n{'=' * 60}\n[{step}] {script}\n{'=' * 60}", flush=True)
        # UTF-8 mode: token lists contain characters (curly quotes, '…', '→') that the
        # default Windows codepage cannot print.
        env = {**os.environ, "PYTHONUTF8": "1"}
        if subprocess.run([sys.executable, str(SCRIPTS / script)], env=env).returncode != 0:
            sys.exit(f"step {step} ({script}) failed; stopping.")
    print("\ndone. metrics in results/, charts in figures/")


if __name__ == "__main__":
    main()
