"""
Utility helpers: logging, progress display, path resolution.
"""

import logging
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the root logger for the converter."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
    )
    # Silence noisy third-party loggers
    for noisy in ("omni", "carb", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("cad_converter")


def get_logger(name: str = "cad_converter") -> logging.Logger:
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Progress bar (no external deps)
# ---------------------------------------------------------------------------

class ProgressBar:
    """Simple terminal progress bar that works without 'tqdm'."""

    def __init__(self, total: int, label: str = "", width: int = 40):
        self.total = max(total, 1)
        self.label = label
        self.width = width
        self._current = 0
        self._start = time.monotonic()

    def update(self, current: int) -> None:
        self._current = min(current, self.total)
        self._render()

    def increment(self) -> None:
        self.update(self._current + 1)

    def finish(self) -> None:
        self.update(self.total)
        elapsed = time.monotonic() - self._start
        print(f"  Done in {elapsed:.1f}s")

    def _render(self) -> None:
        filled = int(self.width * self._current / self.total)
        bar = "█" * filled + "░" * (self.width - filled)
        pct = int(100 * self._current / self.total)
        label = f"{self.label}: " if self.label else ""
        print(f"\r  {label}[{bar}] {pct:3d}%  ({self._current}/{self.total})",
              end="", flush=True)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def resolve_output_path(input_path: Path, output_arg: str | None,
                        output_format: str = ".usd") -> Path:
    """
    Determine the output USD path from the input path and optional --output arg.

    Rules:
      - If output_arg is None: place output next to input with USD extension.
      - If output_arg is a directory: place output inside it, same stem.
      - Otherwise: use output_arg as-is (must end in a USD extension).
    """
    usd_exts = {".usd", ".usda", ".usdc", ".usdz"}

    if output_arg is None:
        return input_path.with_suffix(output_format)

    out = Path(output_arg)

    if out.is_dir():
        return out / input_path.with_suffix(output_format).name

    if out.suffix.lower() not in usd_exts:
        # Treat as directory that doesn't exist yet
        out.mkdir(parents=True, exist_ok=True)
        return out / input_path.with_suffix(output_format).name

    return out


def find_cad_files(root: Path, recursive: bool = True) -> list[Path]:
    """
    Walk *root* and collect all files with supported CAD extensions.
    Import here to avoid circular import with formats module.
    """
    from src.formats import ALL_SUPPORTED_EXTENSIONS

    pattern = "**/*" if recursive else "*"
    return sorted(
        p for p in root.glob(pattern)
        if p.is_file() and p.suffix.lower() in ALL_SUPPORTED_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# Human-readable size
# ---------------------------------------------------------------------------

def human_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes //= 1024
    return f"{n_bytes:.1f} TB"
