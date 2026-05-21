"""
run_batch.py — Python CLI entry point for batch_convert.bat.

This script runs OUTSIDE Kit (with the system Python) and orchestrates
the BatchConverter, which calls kit.exe per-file via subprocess.

Arguments are passed by batch_convert.bat — see that file for full docs.
"""

import argparse
import sys
from pathlib import Path

# Ensure the repo root is on the Python path so 'src' imports work
import os
sys.path.insert(0, str(Path(__file__).parent))

from src.batch import BatchConverter
from src.converter import CadToUsdConverter
from src.utils import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="run_batch",
                                description="Batch CAD -> USD converter")
    p.add_argument("--input",   required=True, metavar="DIR",
                   help="Input folder to scan")
    p.add_argument("--output",  default="", metavar="DIR",
                   help="Output folder root (empty = next to each input)")
    p.add_argument("--format",  default=".usd", metavar="EXT",
                   help="USD output extension (.usd .usda .usdc .usdz)")

    # Batch options
    p.add_argument("--flat",           action="store_true",
                   help="Do not recurse into subfolders")
    p.add_argument("--skip-existing",  action="store_true",
                   help="Skip files whose USD output already exists")
    p.add_argument("--dry-run",        action="store_true",
                   help="Print what would be converted without converting")

    # Conversion quality options
    p.add_argument("--no-materials",      action="store_true")
    p.add_argument("--single-mesh",       action="store_true")
    p.add_argument("--tessellation-chord", type=float, default=0.01)
    p.add_argument("--tessellation-angle", type=float, default=30.0)
    p.add_argument("--no-meter-units",    action="store_true")
    p.add_argument("--keep-hidden",       action="store_true")
    p.add_argument("--verbose",           action="store_true")

    # Extension filter (may appear multiple times)
    p.add_argument("--ext", action="append", metavar="EXT", default=[],
                   help="Only convert files with this extension (e.g. .prt)")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    log = setup_logging(verbose=args.verbose)

    converter = CadToUsdConverter(
        verbose=args.verbose,
        output_format=args.format,
    )

    batch = BatchConverter(
        converter=converter,
        workers=1,  # Increase if you have concurrent Kit license
        recursive=not args.flat,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        output_format=args.format,
    )

    # Build convert kwargs to forward to each file conversion
    convert_kwargs = dict(
        no_materials=args.no_materials,
        single_mesh=args.single_mesh,
        tessellation_chord=args.tessellation_chord,
        tessellation_angle=args.tessellation_angle,
        no_meter_units=args.no_meter_units,
        keep_hidden=args.keep_hidden,
    )

    # Extension filter
    include_exts = None
    if args.ext:
        include_exts = {e if e.startswith(".") else f".{e}" for e in args.ext}

    summary = batch.run(
        input_dir=args.input,
        output_dir=args.output if args.output else None,
        include_extensions=include_exts,
        **convert_kwargs,
    )

    # Exit 0 if all succeeded, 1 if any failed
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
