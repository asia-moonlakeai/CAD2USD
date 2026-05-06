# CAD to USD Converter

Convert Creo, CATIA, NX, SolidWorks, STEP, IGES, and 20+ other CAD formats
to Universal Scene Description (USD) using NVIDIA **kit-kernel** and
`omni.kit.asset_converter` — installed entirely via pip.

---

## Prerequisites

### 1. Python 3.12 — required, no exceptions
All Windows wheels for `omniverse-kit` are built for `cp312` only. Python 3.10
or 3.11 will fail with "no matching distribution found".

Download Python 3.12: https://python.org/downloads/release/python-3120/

If you have multiple Python versions installed, use the launcher to create a 3.12 venv first:
```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
install.bat
```

### 2. CAD Converter license (for proprietary formats)
Formats like Creo, CATIA, NX, and SolidWorks need the **CAD Converter
license extension** (`omni.kit.asset_converter.cad`).

- Available via **Omniverse Enterprise** or your NVIDIA partner account
- Open/neutral formats (STEP, IGES, OBJ, FBX, glTF) work without a license

Contact your NVIDIA account team or visit:
https://developer.nvidia.com/omniverse/enterprise

---

## Installation

```bat
install.bat
```

That's it — fully automated. The installer:

1. **Finds Python 3.12** — checks `py -3.12`, `python3.12`, `python`, and common install paths
2. **Creates `.venv`** — isolated virtual environment in this folder (reused on re-runs)
3. **Installs `omniverse-kit`** from `https://pypi.nvidia.com` (~500 MB, public, no login needed)
4. **Accepts the NVIDIA EULA** non-interactively (`OMNI_KIT_ACCEPT_EULA=yes`)
5. **Writes `config.env`** — stores the venv Python path so all `.bat` scripts use it automatically
6. **Validates** the full installation

You never need to activate the venv manually — `convert.bat`, `batch_convert.bat`,
and `validate.bat` all read the venv Python path from `config.env` and use it directly.

`pypi.nvidia.com` is NVIDIA's **public** index — no account or API key needed.
The `omniverse-kit` listing on `pypi.org` is a placeholder only; the actual wheel
comes from NVIDIA's index.

---

## Usage

### Single file

```bat
convert.bat  "wheel.prt"
convert.bat  "wheel.prt"  "C:\USD\wheel.usd"
convert.bat  "assembly.asm"  "C:\USD\assembly.usd"  --fine
convert.bat  "part.stp"  --no-materials  --verbose
```

### Batch folder

```bat
rem Convert all supported files, output mirrors directory structure
batch_convert.bat  "C:\Models"  "C:\USD"

rem Only Creo parts and assemblies, skip existing outputs
batch_convert.bat  "C:\Models"  "C:\USD"  --ext .prt  --ext .asm  --skip-existing

rem Preview what would be converted
batch_convert.bat  "C:\Models"  --dry-run

rem High quality, text USD output
batch_convert.bat  "C:\Models"  "C:\USD"  --fine  --usda
```

### Python API

```python
import sys
sys.path.insert(0, r"C:\path\to\usd-convert-creo")

from src.converter import CadToUsdConverter
from src.batch import BatchConverter

# Single file
conv = CadToUsdConverter()
result = conv.convert("wheel.prt", "wheel.usd", tessellation_chord=0.005)
print(result)  # [OK] wheel.prt -> wheel.usd (12.4 MB, 8.3s)

# Batch
batch = BatchConverter(skip_existing=True)
summary = batch.run("./cad_models", "./usd_output")
print(f"Converted {summary.succeeded}/{summary.total} files")
```

---

## Options

### Tessellation Quality

| Flag      | Chord  | Angle | Use Case                      |
|-----------|--------|-------|-------------------------------|
| `--coarse`| 0.1    | 45°   | Fast preview, layout work     |
| *(default)*| 0.01  | 30°   | Balanced (most use cases)     |
| `--fine`  | 0.001  | 10°   | High fidelity, hero assets    |

Custom: `--tessellation-chord 0.005 --tessellation-angle 20`

### Output Format

| Flag     | Ext    | Description                                  |
|----------|--------|----------------------------------------------|
| *(default)*| `.usd`| Binary USD (compact, fast to load)          |
| `--usda` | `.usda`| ASCII/text (human-readable, git-diffable)    |
| `--usdc` | `.usdc`| Explicit binary                              |
| `--usdz` | `.usdz`| Zip package (AR, mobile, sharing)            |

### Other Flags

| Flag              | Description                                        |
|-------------------|----------------------------------------------------|
| `--no-materials`  | Skip material/texture conversion                   |
| `--single-mesh`   | Flatten assembly hierarchy into one mesh           |
| `--no-meter-units`| Keep original file units (don't convert to metres) |
| `--keep-hidden`   | Include hidden bodies and components               |
| `--skip-existing` | *(batch)* Skip files with existing USD output      |
| `--dry-run`       | *(batch)* Print plan without converting            |
| `--flat`          | *(batch)* Don't recurse into subfolders            |
| `--verbose`       | Show detailed output                               |
| `--formats`       | Print all supported input formats and exit         |

---

## Supported Formats

Run `convert.bat --formats` for the full table.

| Format | Extensions | License |
|--------|------------|---------|
| PTC Creo | `.prt` `.asm` `.xpr` `.xas` | CAD License |
| CATIA V5/V6 | `.CATPart` `.CATProduct` `.3dxml` | CAD License |
| Siemens NX | `.prt` | CAD License |
| SolidWorks | `.sldprt` `.sldasm` | CAD License |
| Inventor | `.ipt` `.iam` | CAD License |
| JT | `.jt` | CAD License |
| STEP | `.stp` `.step` | Included |
| IGES | `.igs` `.iges` | Included |
| Parasolid | `.x_t` `.x_b` | Included |
| OBJ | `.obj` | Included |
| FBX | `.fbx` | Included |
| glTF / GLB | `.gltf` `.glb` | Included |
| STL | `.stl` | Included |

---

## Project Structure

```
usd-convert-creo/
├── install.bat             # One-time pip install + setup
├── convert.bat             # Single file conversion CLI
├── batch_convert.bat       # Batch folder conversion CLI
├── validate.bat            # Re-run environment checks
├── run_batch.py            # Python entry point for batch_convert.bat
├── requirements.txt        # pip dependencies (kit-kernel, omni-kit-asset-converter)
├── config.env.example      # Configuration template
├── config.env              # Your settings (created by install.bat)
│
├── app/
│   ├── run_conversion.py   # Single-file CLI (called by convert.bat)
│   └── cad_converter.kit   # Optional Kit app config for advanced settings
│
├── src/
│   ├── converter.py        # CadToUsdConverter — uses omni.kit.asset_converter
│   ├── batch.py            # BatchConverter — folder scanning + orchestration
│   ├── formats.py          # Supported format registry with metadata
│   └── utils.py            # Logging, progress bar, path helpers
│
└── setup/
    └── validate_env.py     # Environment validator
```

---

## How It Works

```
convert.bat
    └── python app/run_conversion.py --input ... --output ...
            └── src/converter.py
                    └── omni.kit.asset_converter   ← from kit-kernel pip package
                            └── AssetConverterContext + create_converter_task()
                                    └── writes  output.usd
```

kit-kernel brings the full Omniverse Kit runtime into your Python process via pip.
No separate application install, no kit.exe subprocess — just `import omni.*`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'omni'` or `omni.kit_app`**
Run `install.bat` or: `pip install omniverse-kit --extra-index-url https://pypi.nvidia.com`

**Python version error**
`omniverse-kit` requires Python 3.12 exactly. Check with `python --version` and
download 3.12 from https://python.org/downloads if needed.

**EULA prompt blocking a pipeline**
Set the environment variable before running: `set OMNI_KIT_ACCEPT_EULA=yes`

**Conversion fails for Creo/CATIA/NX**
The CAD Converter license extension is required. Run `validate.bat` to check
if it's present. Contact your NVIDIA account team if you need access.

**Large assemblies are slow**
Use `--coarse` for initial passes or exploratory work. The `--single-mesh` flag
trades hierarchy for a significant speed and file-size reduction.
