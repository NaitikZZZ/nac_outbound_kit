#!/usr/bin/env python3
"""Chain csv-normalizer -> hubspot-abm-exclusion into one pass.

Takes a raw prospect CSV and produces two files: one OK to reach out,
one excluded with reasons. Thin orchestration only -- all actual logic
lives in the two skills being called.

Usage:
    python3 run_pipeline.py --in leads.csv --stem outputs/leads
"""
import argparse
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2]
NORMALIZE = SKILLS_DIR / "csv-normalizer" / "scripts" / "normalize.py"
CHECK_EXCLUSIONS = SKILLS_DIR / "hubspot-abm-exclusion" / "scripts" / "check_exclusions.py"


def run(cmd):
    print(f"$ {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="infile", required=True, help="Raw prospect/lead CSV")
    ap.add_argument("--stem", required=True, help="Output path prefix, e.g. outputs/leads")
    ap.add_argument("--cache", help="Exclusion cache CSV (default: hubspot-abm-exclusion's own cache)")
    ap.add_argument("--strip-the", action="store_true")
    ap.add_argument("--strip-tagline", action="store_true")
    ap.add_argument("--strip-geo", action="store_true")
    args = ap.parse_args()

    clean_csv = f"{args.stem}-clean.csv"
    norm_report = f"{args.stem}-normalization-report.md"
    ok_out = f"{args.stem}-ok-to-reach-out.csv"
    excluded_out = f"{args.stem}-excluded.csv"
    summary_out = f"{args.stem}-exclusion-summary.md"

    normalize_cmd = [sys.executable, str(NORMALIZE), "--in", args.infile, "--out", clean_csv, "--report", norm_report]
    for flag in ("strip_the", "strip_tagline", "strip_geo"):
        if getattr(args, flag):
            normalize_cmd.append(f"--{flag.replace('_', '-')}")
    run(normalize_cmd)

    check_cmd = [
        sys.executable, str(CHECK_EXCLUSIONS),
        "--prospects", clean_csv,
        "--ok-out", ok_out,
        "--excluded-out", excluded_out,
        "--summary-out", summary_out,
    ]
    if args.cache:
        check_cmd += ["--cache", args.cache]
    run(check_cmd)

    print(f"\nDone.\n  Normalized:  {clean_csv}\n  QA report:   {norm_report}\n  OK to reach: {ok_out}\n  Excluded:    {excluded_out}\n  Summary:     {summary_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
