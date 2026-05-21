"""
batch.py — Batch CAD -> USD conversion.

Scans a folder (recursively or flat) for supported CAD files and converts
them all, preserving the relative directory structure in the output folder.

Usage (from your own Python):
    from src.batch import BatchConverter
    results = BatchConverter().run(input_dir="./cad", output_dir="./usd")

Or via the CLI:
    batch_convert.bat  C:/Models/CAD  C:/Models/USD
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from src.converter import CadToUsdConverter, ConversionResult
from src.formats import ALL_SUPPORTED_EXTENSIONS, get_format_info
from src.utils import find_cad_files, get_logger, human_size, _cad_stem

log = get_logger()


# ---------------------------------------------------------------------------
# Batch result summary
# ---------------------------------------------------------------------------

@dataclass
class BatchSummary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    total_elapsed: float = 0.0
    total_output_bytes: int = 0
    results: list[ConversionResult] = field(default_factory=list)

    @property
    def failed_results(self) -> list[ConversionResult]:
        return [r for r in self.results if not r.success]

    def print_report(self) -> None:
        print()
        print("=" * 65)
        print("  Batch Conversion Summary")
        print("=" * 65)
        print(f"  Total files   : {self.total}")
        print(f"  Succeeded     : {self.succeeded}")
        print(f"  Failed        : {self.failed}")
        print(f"  Skipped       : {self.skipped}")
        print(f"  Output size   : {human_size(self.total_output_bytes)}")
        print(f"  Total time    : {self.total_elapsed:.1f}s")
        if self.total > 0:
            avg = self.total_elapsed / max(self.succeeded + self.failed, 1)
            print(f"  Avg per file  : {avg:.1f}s")

        if self.failed_results:
            print()
            print("  Failed files:")
            for r in self.failed_results:
                print(f"    ✗ {r.input_path.name}")
                print(f"      {r.error_message}")

        print("=" * 65)
        print()


# ---------------------------------------------------------------------------
# Batch converter
# ---------------------------------------------------------------------------

class BatchConverter:
    """
    Discover and convert all supported CAD files in a directory tree.
    """

    def __init__(
        self,
        converter: CadToUsdConverter | None = None,
        workers: int = 1,
        recursive: bool = True,
        skip_existing: bool = False,
        dry_run: bool = False,
        output_format: str = ".usd",
    ):
        """
        Args:
            converter:     A pre-configured CadToUsdConverter instance.
                           Created with defaults if None.
            workers:       Parallel conversion workers. Keep at 1 unless you
                           have tested your Kit license for concurrent use.
            recursive:     Recurse into subdirectories.
            skip_existing: Skip files whose output USD already exists.
            dry_run:       Print what would be converted without doing it.
            output_format: USD output extension (.usd, .usda, .usdc, .usdz).
        """
        self.converter   = converter or CadToUsdConverter(output_format=output_format)
        self.workers     = workers
        self.recursive   = recursive
        self.skip_existing = skip_existing
        self.dry_run     = dry_run
        self.output_format = output_format

    def run(
        self,
        input_dir: Path | str,
        output_dir: Path | str | None = None,
        include_extensions: set[str] | None = None,
        exclude_extensions: set[str] | None = None,
        **convert_kwargs,
    ) -> BatchSummary:
        """
        Discover and convert all CAD files under *input_dir*.

        Args:
            input_dir:           Root directory to scan.
            output_dir:          Root directory for USD output. If None,
                                 output is placed next to each input file.
            include_extensions:  Whitelist of extensions (e.g. {'.prt','.asm'}).
                                 If None, all supported formats are included.
            exclude_extensions:  Blacklist of extensions to skip.
            **convert_kwargs:    Forwarded to CadToUsdConverter.convert().

        Returns:
            BatchSummary with per-file results.
        """
        input_dir  = Path(input_dir).resolve()
        output_dir = Path(output_dir).resolve() if output_dir else None

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        # --- Discover files ---
        all_files = find_cad_files(input_dir, recursive=self.recursive)

        # Apply extension filters
        if include_extensions:
            include_extensions = {e.lower() for e in include_extensions}
            all_files = [f for f in all_files
                         if f.suffix.lower() in include_extensions]
        if exclude_extensions:
            exclude_extensions = {e.lower() for e in exclude_extensions}
            all_files = [f for f in all_files
                         if f.suffix.lower() not in exclude_extensions]

        summary = BatchSummary(total=len(all_files))
        t_batch_start = time.monotonic()

        if not all_files:
            print("  No supported CAD files found in:", input_dir)
            return summary

        print(f"\n  Found {len(all_files)} file(s) to convert")
        if output_dir:
            print(f"  Output root: {output_dir}")
        print()

        if self.dry_run:
            print("  [DRY RUN] Files that would be converted:")
            for f in all_files:
                out = self._output_path(f, input_dir, output_dir)
                print(f"    {f.relative_to(input_dir)}  ->  {out}")
            print()
            return summary

        # --- Convert ---
        if self.workers > 1:
            results = self._run_parallel(all_files, input_dir, output_dir,
                                         convert_kwargs)
        else:
            results = self._run_sequential(all_files, input_dir, output_dir,
                                           convert_kwargs)

        summary.results       = results
        summary.total_elapsed = time.monotonic() - t_batch_start
        summary.succeeded     = sum(1 for r in results if r.success)
        summary.failed        = sum(1 for r in results if not r.success)
        summary.total_output_bytes = sum(
            r.output_size_bytes for r in results if r.success
        )

        summary.print_report()
        return summary

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _output_path(self, input_file: Path, input_root: Path,
                     output_root: Path | None) -> Path:
        """
        Compute the output USD path preserving relative directory structure.
        Strips Creo version suffixes (e.g. wheel.prt.1 -> wheel.usd).
        """
        usd_name = _cad_stem(input_file) + self.output_format

        if output_root is None:
            return input_file.parent / usd_name

        rel_dir = input_file.relative_to(input_root).parent
        return output_root / rel_dir / usd_name

    def _should_skip(self, output_path: Path) -> bool:
        return self.skip_existing and output_path.exists()

    def _convert_one(self, input_file: Path, input_root: Path,
                     output_root: Path | None,
                     convert_kwargs: dict,
                     index: int, total: int) -> ConversionResult:
        out_path = self._output_path(input_file, input_root, output_root)

        prefix = f"  [{index:>{len(str(total))}}/{total}]"
        fmt = get_format_info(input_file)
        fmt_name = fmt.name if fmt else input_file.suffix.upper()
        print(f"{prefix} {input_file.name}  ({fmt_name})")

        if self._should_skip(out_path):
            print(f"         -> Skipping (output exists): {out_path.name}")
            return ConversionResult(
                input_path=input_file,
                output_path=out_path,
                success=True,
                error_message="skipped (output exists)",
            )

        result = self.converter.convert(
            input_path=input_file,
            output_path=out_path,
            **convert_kwargs,
        )
        print(f"         -> {result}")
        return result

    def _run_sequential(self, files: list[Path], input_root: Path,
                        output_root: Path | None,
                        convert_kwargs: dict) -> list[ConversionResult]:
        results = []
        for i, f in enumerate(files, 1):
            results.append(
                self._convert_one(f, input_root, output_root,
                                  convert_kwargs, i, len(files))
            )
        return results

    def _run_parallel(self, files: list[Path], input_root: Path,
                      output_root: Path | None,
                      convert_kwargs: dict) -> list[ConversionResult]:
        results: list[ConversionResult] = [None] * len(files)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            future_to_idx = {
                pool.submit(
                    self._convert_one, f, input_root, output_root,
                    convert_kwargs, i + 1, len(files)
                ): i
                for i, f in enumerate(files)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    results[idx] = ConversionResult(
                        input_path=files[idx],
                        output_path=Path("unknown"),
                        success=False,
                        error_message=str(exc),
                    )
        return results
