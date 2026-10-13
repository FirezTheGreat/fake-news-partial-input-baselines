"""Run the whole pipeline, or chosen steps.

    run              everything: 0 (fetch and verify data), then 1-6, then 7 (figures)
    run 2            only step 2
    run 3 7          steps 3 and 7, in that order

With no arguments, steps 1-6 run three at a time once the spaCy/VADER caches in
data/cache/ exist (they are independent of each other); their output goes to
results/logs/step_N.log. Without the caches they run one at a time, because each
cache is built by whichever step needs it first. Results are identical either way.
"""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
LOGS = ROOT / "results" / "logs"
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
INDEPENDENT = ["5", "4", "6", "3", "2", "1"]  # steps 1-6, longest first
CACHES = ["function_words", "stripped_profile", "sentiment", "mcintire_profile"]
PARALLEL_STEPS = 3  # each step already fits 5 splits in parallel; 3 x 5 suits a 16-core machine

# UTF-8 mode: token lists contain characters (curly quotes, '…', '→') that the
# default Windows codepage cannot print.
ENV = {**os.environ, "PYTHONUTF8": "1"}


def run_step(step, log_file=None):
    """Run one step; return (step, seconds, return code)."""
    start = time.perf_counter()
    cmd = [sys.executable, str(SCRIPTS / STEPS[step])]
    if log_file is None:
        code = subprocess.run(cmd, env=ENV).returncode
    else:
        with open(log_file, "w", encoding="utf-8") as log:
            code = subprocess.run(cmd, env=ENV, stdout=log, stderr=subprocess.STDOUT).returncode
    return step, time.perf_counter() - start, code


def run_in_order(steps, timings):
    for step in steps:
        print(f"\n{'=' * 60}\n[{step}] {STEPS[step]}\n{'=' * 60}", flush=True)
        step, seconds, code = run_step(step)
        if code != 0:
            sys.exit(f"step {step} ({STEPS[step]}) failed; stopping.")
        timings.append((step, seconds))


def run_in_parallel(steps, timings):
    LOGS.mkdir(parents=True, exist_ok=True)
    print(f"\nrunning steps {', '.join(sorted(steps))} ({PARALLEL_STEPS} at a time); "
          f"output in {LOGS.relative_to(ROOT)}", flush=True)
    failed = []
    with ThreadPoolExecutor(max_workers=PARALLEL_STEPS) as pool:
        futures = [pool.submit(run_step, s, LOGS / f"step_{s}.log") for s in steps]
        for future in as_completed(futures):
            step, seconds, code = future.result()
            status = "done" if code == 0 else "FAILED"
            print(f"  [{step}] {STEPS[step]:<22} {status} in {seconds / 60:.1f} min", flush=True)
            if code == 0:
                timings.append((step, seconds))
            else:
                failed.append(step)
    if failed:
        sys.exit(f"step(s) {', '.join(failed)} failed; see results/logs/step_N.log")


def main():
    chosen = sys.argv[1:]
    unknown = [s for s in chosen if s not in STEPS]
    if unknown:
        sys.exit(f"unknown step(s): {', '.join(unknown)}. Choose from {', '.join(STEPS)}.")

    start = time.perf_counter()
    timings = []
    if chosen:
        run_in_order(chosen, timings)
    else:
        run_in_order(["0"], timings)
        caches_ready = all((ROOT / "data" / "cache" / f"{c}.json").exists() for c in CACHES)
        if caches_ready:
            run_in_parallel(INDEPENDENT, timings)
        else:
            print("\nspaCy/VADER caches not built yet: running steps one at a time this once")
            run_in_order(sorted(INDEPENDENT), timings)
        run_in_order(["7"], timings)

    print("\ntime per step:")
    for step, seconds in sorted(timings):
        print(f"  [{step}] {STEPS[step]:<22} {seconds / 60:5.1f} min")
    print(f"  wall-clock total {(time.perf_counter() - start) / 60:.1f} min")
    print("\ndone. metrics in results/, charts in figures/")


if __name__ == "__main__":
    main()
