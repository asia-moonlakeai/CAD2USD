# CAD2USD — Agent Guide

Convert CAD files (Creo, CATIA, NX, SolidWorks, STEP, IGES, and 20+ formats) to Universal Scene Description (USD) using NVIDIA Omniverse Kit installed entirely via pip.

---

## Critical Environment Constraints

**Python 3.12 only — no exceptions.** The `omniverse-kit` wheel is built for `cp312`. Python 3.10 or 3.11 will fail at install time.

**Windows only.** The `omniverse-kit` pip package currently ships Windows wheels only (`windows-x86_64`). Do not attempt to run conversions on Linux or macOS.

**NVIDIA EULA.** On first run, the Kit runtime prompts for EULA acceptance. Set `OMNI_KIT_ACCEPT_EULA=yes` in the environment to accept non-interactively (pipelines, CI, headless).

**CAD license required for proprietary formats.** Creo (`.prt`, `.asm`), CATIA, NX, SolidWorks, and JT need the `omni.kit.converter.cad` extension, which requires an Omniverse Enterprise license. Open formats (STEP, IGES, OBJ, FBX, glTF, STL, Parasolid) work without any license.

---

## Setup

```bat
install.bat
```

This creates `.venv` with Python 3.12, installs `omniverse-kit` from `https://pypi.nvidia.com`, and writes `config.env` with the venv Python path. All `.bat` scripts source `config.env` automatically — never activate the venv manually.

To install manually:
```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install omniverse-kit --extra-index-url https://pypi.nvidia.com
```

---

## Key Commands

```bat
# Validate environment (run after install or after changes)
validate.bat

# Convert a single file
convert.bat "path\to\part.prt"
convert.bat "path\to\part.prt" "C:\USD\part.usd" --fine

# Batch convert a folder
batch_convert.bat "C:\CAD" "C:\USD"
batch_convert.bat "C:\CAD" "C:\USD" --skip-existing --dry-run

# List all supported input formats
convert.bat --formats
```

---

## Project Structure

```
CAD2USD/
├── install.bat             # One-time setup: creates .venv, installs omniverse-kit
├── convert.bat             # Single-file conversion CLI
├── batch_convert.bat       # Batch folder conversion CLI
├── validate.bat            # Re-run environment checks
├── run_batch.py            # Python entry point for batch_convert.bat
├── requirements.txt        # pip deps (omniverse-kit from pypi.nvidia.com)
├── config.env.example      # Template — copy to config.env and fill in
├── config.env              # Your local settings (gitignored)
│
├── app/
│   ├── run_conversion.py   # CLI entry point called by convert.bat
│   └── cad_converter.kit   # Optional Kit app config for advanced settings
│
├── src/
│   ├── converter.py        # CadToUsdConverter class — core conversion logic
│   ├── batch.py            # BatchConverter — folder scanning + orchestration
│   ├── formats.py          # FORMATS registry: all supported extensions + metadata
│   └── utils.py            # Logging, progress bar, path helpers
│
└── setup/
    ├── validate_env.py     # Checks Python version, omni install, CAD license
    ├── find_kit.py         # Locates kit-kernel install path
    └── fetch_cad_ext.py    # Downloads the CAD converter extension from NVIDIA registry
```

---

## Architecture

### Dual conversion pipeline

Conversion is routed based on file format:

```
input file
  ├── CAD format (Creo, CATIA, NX, SolidWorks, JT, Inventor…)
  │     └── omni.kit.converter.hoops_core  (HOOPS Exchange)
  └── Open format (STEP, IGES, OBJ, FBX, glTF, STL, Parasolid…)
        └── omni.kit.asset_converter
```

`src/formats.py` drives routing via `requires_cad_license` on each `FormatInfo`. `src/converter.py:_is_cad_format()` does the dispatch.

### KitApp singleton

`omni.kit_app.KitApp` **must be the first omni import** in the process — it bootstraps Carbonite and sets library paths. It is started lazily on the first call to `CadToUsdConverter.convert()` and kept alive for the process lifetime. Call `converter.shutdown()` or `shutdown_kit()` when done with all conversions to cleanly tear it down.

### Python API

```python
from src.converter import CadToUsdConverter

conv = CadToUsdConverter()

# Single file — output auto-placed next to input if path omitted
result = conv.convert("wheel.prt", "wheel.usd", tessellation_chord=0.005)
print(result)  # [OK] wheel.prt -> wheel.usd (12.4 MB, 8.3s)

conv.shutdown()
```

```python
from src.batch import BatchConverter

batch = BatchConverter(skip_existing=True)
summary = batch.run("./cad_models", "./usd_output")
print(f"Converted {summary.succeeded}/{summary.total} files")
```

---

## Tessellation Quality

| Flag | Chord | Angle | Use Case |
|---|---|---|---|
| `--coarse` | 0.1 | 45° | Fast preview |
| *(default)* | 0.01 | 30° | Balanced |
| `--fine` | 0.001 | 10° | High fidelity |

Custom: `--tessellation-chord 0.005 --tessellation-angle 20`

---

## Output Formats

| Flag | Ext | Notes |
|---|---|---|
| *(default)* | `.usd` | Binary — compact, fast to load |
| `--usda` | `.usda` | ASCII — human-readable, git-diffable |
| `--usdc` | `.usdc` | Explicit binary |
| `--usdz` | `.usdz` | Zip package — for AR, mobile, sharing |

---

## Adding a New Format

1. Add a `FormatInfo` entry to `FORMATS` in `src/formats.py`.
2. Set `requires_cad_license=True` if the format needs HOOPS Exchange, `False` if `omni.kit.asset_converter` handles it natively.
3. Run `convert.bat --formats` to verify it appears in the table.
4. Test with a sample file. If routing is wrong, adjust `_is_cad_format()` in `src/converter.py`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `No module named 'omni'` | `omniverse-kit` not installed | Run `install.bat` |
| `no matching distribution found` | Wrong Python version | Use Python 3.12 exactly |
| EULA prompt blocks pipeline | Interactive mode | Set `OMNI_KIT_ACCEPT_EULA=yes` |
| Conversion fails for Creo/CATIA/NX | CAD license not present | Run `validate.bat`; contact NVIDIA account team |
| `HOOPS converter instance is None` | `omni.kit.converter.cad` didn't finish loading | Wait for KitApp startup to complete; check NVIDIA registry connectivity |
| Large assembly is slow | Default tessellation is fine | Use `--coarse` for initial passes |

---

## Testing

There is no automated test suite yet. To smoke-test:

```bat
# Verify environment is healthy
validate.bat

# Convert the included sample (open format — no license needed)
convert.bat test.prt --verbose
```

When adding tests, use `test.prt` as the sample fixture. Do not commit large CAD assemblies to the repo. Mock `omni.kit.asset_converter` for unit tests that don't need the full Kit runtime.

---

## What Not to Commit

- `.venv/` — regenerated by `install.bat`
- `config.env` — contains local paths; use `config.env.example` as the template
- `__pycache__/`, `*.pyc`
- Omniverse Kit cache directories (`omni_cache/`, `_build/`, `kit/`)
- Large CAD assembly files

All of the above are covered by `.gitignore`.
