"""
run_conversion.py — CLI entry point for single-file conversion.

Now that kit-kernel is a pip package, this script runs with the standard
Python interpreter — no kit.exe subprocess required.

Usage:
    python app\run_conversion.py --input wheel.prt --output wheel.usd
    python app\run_conversion.py --input assembly.asm --output assembly.usd --fine

Called by convert.bat. Can also be used directly.
"""

import argparse
import sys
from pathlib import Path

# Ensure repo root is on path for 'src.*' imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converter import CadToUsdConverter
from src.formats import get_format_info, is_supported, print_format_table
from src.utils import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_conversion",
        description="Convert a CAD file to USD using NVIDIA kit-kernel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app\\run_conversion.py --input wheel.prt --output wheel.usd
  python app\\run_conversion.py --input assembly.asm --fine --no-materials
  python app\\run_conversion.py --formats
        """,
    )
    p.add_argument("--input",  metavar="PATH",
                   help="Input CAD file path")
    p.add_argument("--output", metavar="PATH", default=None,
                   help="Output USD path (default: next to input with .usd extension)")
    p.add_argument("--format", default=".usd", dest="usd_format",
                   choices=[".usd", ".usda", ".usdc", ".usdz"],
                   help="USD output format (default: .usd)")

    # Tessellation quality shortcuts
    quality = p.add_mutually_exclusive_group()
    quality.add_argument("--fine",   action="store_true",
                         help="Fine tessellation: chord=0.001, angle=10°")
    quality.add_argument("--coarse", action="store_true",
                         help="Coarse tessellation: chord=0.1, angle=45°")
    quality.add_argument("--tessellation-chord", type=float, default=0.01,
                         metavar="N", dest="chord",
                         help="Max chord deviation (default: 0.01)")

    p.add_argument("--tessellation-angle", type=float, default=30.0,
                   metavar="DEG", dest="angle",
                   help="Max normal angle error in degrees (default: 30)")
    p.add_argument("--no-materials",  action="store_true")
    p.add_argument("--single-mesh",   action="store_true")
    p.add_argument("--no-meter-units", action="store_true")
    p.add_argument("--keep-hidden",   action="store_true")
    p.add_argument("--verbose",       action="store_true")
    p.add_argument("--formats",       action="store_true",
                   help="Print all supported input formats and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.formats:
        print_format_table()
        return 0

    if not args.input:
        print("[ERROR] --input is required. Use --formats to list supported formats.")
        return 2

    log = setup_logging(verbose=args.verbose)

    # Resolve tessellation from quality presets
    chord = args.chord
    angle = args.angle
    if args.fine:
        chord, angle = 0.001, 10.0
    elif args.coarse:
        chord, angle = 0.1, 45.0

    input_path = Path(args.input)
    fmt = get_format_info(input_path)

    print()
    print(f"  Input  : {input_path}")
    if fmt:
        print(f"  Format : {fmt.name}"
              + (" (CAD license required)" if fmt.requires_cad_license else ""))
    print(f"  Output : {args.output or '(auto-placed next to input)'}")
    print(f"  Tessell: chord={chord}, angle={angle}°")
    print()

    conv = CadToUsdConverter(
        output_format=args.usd_format,
        verbose=args.verbose,
    )

    result = conv.convert(
        input_path=args.input,
        output_path=args.output,
        no_materials=args.no_materials,
        single_mesh=args.single_mesh,
        tessellation_chord=chord,
        tessellation_angle=angle,
        no_meter_units=args.no_meter_units,
        keep_hidden=args.keep_hidden,
    )

    print(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
