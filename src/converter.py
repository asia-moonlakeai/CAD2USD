"""
converter.py — CAD to USD conversion using the omniverse-kit pip package.

The 'omniverse-kit' package installs the NVIDIA Omniverse Kit runtime as a
standard Python package, giving direct in-process access to omni.* APIs.

Install:
    pip install omniverse-kit --extra-index-url https://pypi.nvidia.com

Requires Python 3.12. On first run, accept the EULA prompt (one-time).
For headless/non-interactive use, set: OMNI_KIT_ACCEPT_EULA=yes

Usage:
    from src.converter import CadToUsdConverter

    conv = CadToUsdConverter()
    result = conv.convert("wheel.prt", "wheel.usd")
    print(result)
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.formats import get_format_info, is_supported
from src.utils import get_logger, resolve_output_path

log = get_logger()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ConversionResult:
    input_path: Path
    output_path: Path
    success: bool
    elapsed_seconds: float = 0.0
    error_message: str = ""
    output_size_bytes: int = 0

    def __str__(self) -> str:
        if self.success:
            mb = self.output_size_bytes / 1024 / 1024
            return (f"[OK] {self.input_path.name} -> {self.output_path.name} "
                    f"({mb:.1f} MB, {self.elapsed_seconds:.1f}s)")
        return f"[FAIL] {self.input_path.name}: {self.error_message}"


# ---------------------------------------------------------------------------
# KitApp singleton
# ---------------------------------------------------------------------------
# IMPORTANT: 'from omni.kit_app import KitApp' MUST be the first omniverse
# import in the process — it bootstraps Carbonite, sets library paths, etc.
# We defer the import to the first call to ensure nothing else has imported
# omni.* before us.

_app = None  # KitApp instance (kept alive for the process lifetime)


def _find_ov_launcher_ext_folders() -> list[str]:
    """
    Scan the Omniverse Launcher package cache for installed apps that may
    contain the CAD Converter extension (omni.kit.asset_converter.cad).

    Returns a list of --ext-folder paths to pass to KitApp.startup().
    """
    import glob
    folders = []

    # Omniverse Launcher caches apps here on Windows
    ov_pkg = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ov", "pkg")
    if not os.path.isdir(ov_pkg):
        return folders

    # Apps that ship the CAD Converter extension
    cad_app_patterns = [
        "cad-converter-*",
        "create-*",
        "usd-composer-*",
        "omni.create-*",
    ]
    for pattern in cad_app_patterns:
        for app_dir in glob.glob(os.path.join(ov_pkg, pattern)):
            extscache = os.path.join(app_dir, "extscache")
            exts = os.path.join(app_dir, "exts")
            for d in (extscache, exts):
                if os.path.isdir(d) and d not in folders:
                    folders.append(d)
                    log.debug("Found Omniverse ext folder: %s", d)

    return folders


def _ensure_kit_started(extra_extensions: list[str] | None = None) -> None:
    """
    Start the KitApp runtime if not already running.

    The KitApp is a process-level singleton — call this once before any
    omni.kit.asset_converter usage. It is safe to call multiple times.
    """
    global _app
    if _app is not None:
        return

    # Accept EULA non-interactively in pipeline/headless environments
    os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "yes")

    try:
        # This MUST be the first omni import — sets up Carbonite + paths
        from omni.kit_app import KitApp  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "\n\nCould not import omni.kit_app (omniverse-kit package not found).\n\n"
            "Install it with:\n"
            "    pip install omniverse-kit --extra-index-url https://pypi.nvidia.com\n\n"
            "Or run:  install.bat\n\n"
            "Requires Python 3.12."
        ) from exc

    _app = KitApp()

    # Extensions to load:
    #   omni.kit.asset_converter  — base converter (open formats: STEP, IGES, OBJ, FBX, glTF)
    #   omni.kit.converter.cad    — CAD format translators (Creo, CATIA, NX, SolidWorks, JT…)
    #                               auto-downloaded from the NVIDIA extension registry on first run
    extensions_to_enable = [
        "omni.kit.asset_converter",
        "omni.kit.converter.cad",
    ]
    if extra_extensions:
        extensions_to_enable.extend(extra_extensions)

    # Kit 110 shared extension registry (Azure CDN)
    # omni.kit.converter.cad lives here and is downloaded on first use
    _KIT_MAJOR = "110"
    _REG_URL = (
        f"https://ovextensionsprod.blob.core.windows.net"
        f"/exts/kit/prod/{_KIT_MAJOR}/shared"
    )

    startup_args = [
        # Headless — no window, no renderer, no GPU required
        "--no-window",
        "--/app/window/hideUi=true",
        "--/renderer/enabled=false",
        "--/app/renderer/enabled=false",
        "--/app/runLoops/main/rateLimitEnabled=false",
        # EULA
        "--/app/privacy/eula/accept=true",
        "--/app/privacy/consent/accept=true",
        # Extension registry — Kit 110 shared CDN
        "--/app/extensions/registryEnabled=true",
        "--/app/extensions/supportedTargets/platform=windows-x86_64",
        "--enable", "omni.kit.registry.nucleus",
        "--/exts/omni.kit.registry.nucleus/registries/0/name=kit/shared",
        f"--/exts/omni.kit.registry.nucleus/registries/0/url={_REG_URL}",
    ]

    # If Omniverse Launcher apps are installed, add their extension caches too
    for folder in _find_ov_launcher_ext_folders():
        startup_args += ["--ext-folder", folder]
        log.debug("Added Omniverse ext folder: %s", folder)

    for ext in extensions_to_enable:
        startup_args += ["--enable", ext]

    log.debug("Starting KitApp with args: %s", startup_args)
    _app.startup(startup_args)

    # Report whether the CAD translator extension actually loaded
    try:
        import omni.kit.app as _kit_app  # noqa: PLC0415
        mgr = _kit_app.get_app().get_extension_manager()
        cad_targets = ["omni.kit.converter.cad", "omni.kit.converter.hoops"]
        cad_loaded = False
        for name in cad_targets:
            # Kit 110 API
            if hasattr(mgr, "get_enabled_extension_id") and mgr.get_enabled_extension_id(name):
                cad_loaded = True
                break
            # Older API shape
            if hasattr(mgr, "is_extension_present") and mgr.is_extension_present(name):
                cad_loaded = True
                break
        # Also check sys.modules as a fallback
        if not cad_loaded:
            cad_loaded = any(k.startswith("omni.kit.converter") for k in sys.modules)

        if cad_loaded:
            log.info("CAD converter loaded — Creo/CATIA/NX/SolidWorks enabled")
        else:
            log.warning(
                "omni.kit.converter.cad did not load. "
                "Run install.bat to download it from the NVIDIA registry."
            )
    except Exception:
        pass  # extension manager check is non-fatal

    log.debug("KitApp started. omni.kit.asset_converter is ready.")


def shutdown_kit() -> None:
    """
    Cleanly shut down the KitApp. Call this when your script is done
    with all conversions (e.g. at the end of a batch run).
    """
    global _app
    if _app is not None:
        try:
            _app.shutdown()
        except Exception:
            pass
        _app = None


# ---------------------------------------------------------------------------
# Progress callback factory
# ---------------------------------------------------------------------------

def _make_progress_cb(label: str = "") -> Callable[[int, int], None]:
    """Return a callback that prints a terminal progress bar."""
    prefix = f"{label}: " if label else ""
    last = [-1]

    def on_progress(current: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(100 * current / total)
        if pct == last[0]:
            return
        last[0] = pct
        width = 35
        filled = int(width * pct / 100)
        bar = "█" * filled + "░" * (width - filled)
        print(f"\r  {prefix}[{bar}] {pct:3d}%", end="", flush=True)

    return on_progress


# ---------------------------------------------------------------------------
# Conversion pipelines
# ---------------------------------------------------------------------------

# CAD formats (Creo, CATIA, NX, SolidWorks, JT, Inventor…) use the HOOPS
# Exchange translator via omni.kit.converter.hoops_core.
#
# Open formats (STEP, IGES, OBJ, FBX, glTF, STL…) go through the standard
# omni.kit.asset_converter pipeline.
#
# omni.kit.converter.cad is the bundle extension that brings in hoops_core
# plus the DGN and JT sub-converters as dependencies.

def _is_cad_format(path: Path) -> bool:
    """Return True if this file should be converted via HOOPS Exchange."""
    from src.formats import get_format_info  # noqa: PLC0415
    fmt = get_format_info(path)
    # If format is unknown, try HOOPS — it identifies formats by content too
    return fmt is None or fmt.requires_cad_license


async def _run_hoops_async(
    input_path: Path,
    output_path: Path,
    *,
    no_materials: bool = False,
    single_mesh: bool = False,
    tessellation_chord: float = 0.01,
    tessellation_angle: float = 30.0,
    no_meter_units: bool = False,
    keep_hidden: bool = False,
    on_progress: Callable | None = None,
) -> None:
    """
    Convert via omni.kit.converter.hoops_core (HOOPS Exchange).
    Used for proprietary CAD formats: Creo, CATIA, NX, SolidWorks, JT, etc.
    """
    try:
        import omni.kit.converter.hoops_core as hoops  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "omni.kit.converter.hoops_core not found. "
            "Run install.bat to download the CAD converter extension "
            "from the NVIDIA registry."
        ) from exc

    converter = hoops.get_instance()
    if converter is None:
        raise RuntimeError(
            "HOOPS converter instance is None — "
            "omni.kit.converter.cad may not have finished loading."
        )

    progress_cb = on_progress or _make_progress_cb(input_path.name)

    def _s(v) -> str:
        """Convert any value to the string HOOPS Parameters.parseArgs() expects."""
        if isinstance(v, bool):
            return "true" if v else "false"
        return str(v)

    # HOOPS Exchange conversion options — all values must be strings
    options: dict[str, str] = {
        "instancing":       _s(True),
        "bOptimize":        _s(True),
        "convertHidden":    _s(keep_hidden),
        "dMetersPerUnit":   _s(0.0 if no_meter_units else 1.0),
        "iUpAxis":          _s(2),              # Z-up (CAD convention)
        "dChordHeight":     _s(tessellation_chord),
        "dAngleTolerance":  _s(tessellation_angle),
        "importMaterials":  _s(not no_materials),
        "singleMesh":       _s(single_mesh),
    }

    # create_converter_task(input, output, options) — no progress callback
    task = converter.create_converter_task(
        str(input_path),
        str(output_path),
        options,
    )

    # Handle both: task object with wait_until_finished(), or a direct coroutine
    if hasattr(task, "wait_until_finished"):
        success = await task.wait_until_finished()
        print()
        if not success:
            status = getattr(task, "get_status", lambda: "FAILED")()
            raise RuntimeError(f"HOOPS conversion failed [{status}] for {input_path.name}")
    else:
        # Coroutine / future — await directly
        result = await task
        print()
        if result is False:
            raise RuntimeError(f"HOOPS conversion failed for {input_path.name}")


async def _run_asset_converter_async(
    input_path: Path,
    output_path: Path,
    *,
    no_materials: bool = False,
    single_mesh: bool = False,
    tessellation_chord: float = 0.01,
    tessellation_angle: float = 30.0,
    no_meter_units: bool = False,
    keep_hidden: bool = False,
    on_progress: Callable | None = None,
) -> None:
    """
    Convert via omni.kit.asset_converter.
    Used for open formats: STEP, IGES, OBJ, FBX, glTF, STL.
    """
    import omni.kit.asset_converter as converter_module  # noqa: PLC0415

    ctx = converter_module.AssetConverterContext()
    ctx.ignore_materials                     = no_materials
    ctx.export_preview_surface               = not no_materials
    ctx.export_mdl                           = not no_materials
    ctx.single_mesh                          = single_mesh
    ctx.merge_all_meshes                     = single_mesh
    ctx.smooth_normals                       = True
    ctx.ignore_pivots                        = False
    ctx.export_hidden_props                  = keep_hidden
    ctx.ignore_animations                    = True
    ctx.ignore_cameras                       = True
    ctx.ignore_lights                        = True
    ctx.use_meter_as_world_unit              = not no_meter_units
    ctx.tessellation_max_chord_error         = tessellation_chord
    ctx.tessellation_max_normal_error        = tessellation_angle
    ctx.tessellation_max_edge_length_ratio   = 0.0
    ctx.use_double_precision_to_usd_transform_op = True
    ctx.create_world_as_default_root_prim        = False

    progress_cb = on_progress or _make_progress_cb(input_path.name)
    task = converter_module.get_instance().create_converter_task(
        str(input_path), str(output_path), progress_cb, ctx,
    )
    success = await task.wait_until_finished()
    print()
    if not success:
        status = task.get_status()
        detail = (
            task.get_error_message()  if hasattr(task, "get_error_message")  else
            task.get_detailed_error() if hasattr(task, "get_detailed_error") else
            str(status)
        )
        raise RuntimeError(f"Conversion failed [{status}]: {detail}")


async def _run_conversion_async(
    input_path: Path,
    output_path: Path,
    **kwargs,
) -> None:
    """
    Route to HOOPS (CAD formats) or asset_converter (open formats).
    KitApp must already be started before calling this.
    """
    if _is_cad_format(input_path):
        log.debug("Routing %s to HOOPS Exchange converter", input_path.name)
        await _run_hoops_async(input_path, output_path, **kwargs)
    else:
        log.debug("Routing %s to omni.kit.asset_converter", input_path.name)
        await _run_asset_converter_async(input_path, output_path, **kwargs)


# ---------------------------------------------------------------------------
# Public converter class
# ---------------------------------------------------------------------------

class CadToUsdConverter:
    """
    Convert CAD files to USD using the omniverse-kit pip package in-process.

    The KitApp runtime is started on the first conversion and kept alive
    for the lifetime of this object (or until shutdown_kit() is called).

    Example:
        conv = CadToUsdConverter()
        result = conv.convert("engine.asm", "engine.usd")
        if result.success:
            print(f"Done: {result.output_path}")
        conv.shutdown()
    """

    def __init__(
        self,
        output_format: str = ".usd",
        verbose: bool = False,
        extra_extensions: list[str] | None = None,
        auto_accept_eula: bool = True,
    ):
        """
        Args:
            output_format:     Default USD extension (.usd, .usda, .usdc, .usdz).
            verbose:           Enable debug logging.
            extra_extensions:  Additional Kit extension IDs to enable on startup.
            auto_accept_eula:  Set OMNI_KIT_ACCEPT_EULA=yes automatically.
                               Disable if you want to handle EULA yourself.
        """
        self.output_format    = output_format
        self.verbose          = verbose
        self.extra_extensions = extra_extensions or []

        if verbose:
            logging.getLogger("cad_converter").setLevel(logging.DEBUG)

        if auto_accept_eula and not os.environ.get("OMNI_KIT_ACCEPT_EULA"):
            os.environ["OMNI_KIT_ACCEPT_EULA"] = "yes"

    def _ensure_ready(self) -> None:
        _ensure_kit_started(self.extra_extensions)

    def convert(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        no_materials: bool = False,
        single_mesh: bool = False,
        tessellation_chord: float = 0.01,
        tessellation_angle: float = 30.0,
        no_meter_units: bool = False,
        keep_hidden: bool = False,
        on_progress: Callable | None = None,
    ) -> ConversionResult:
        """
        Convert a single CAD file to USD.

        Args:
            input_path:          Source CAD file.
            output_path:         Destination USD file or directory. Auto-placed
                                 next to input if None.
            no_materials:        Skip material/texture conversion.
            single_mesh:         Flatten hierarchy into a single mesh.
            tessellation_chord:  Max chord deviation (smaller = finer mesh).
            tessellation_angle:  Max normal angle error in degrees.
            no_meter_units:      Keep source file units (don't convert to metres).
            keep_hidden:         Include hidden bodies/components.
            on_progress:         Optional callback(current, total) for progress.

        Returns:
            ConversionResult with success flag, timing, and output path.
        """
        # Start KitApp on first use (idempotent)
        self._ensure_ready()

        input_path  = Path(input_path).resolve()
        output_path = resolve_output_path(input_path, output_path,
                                          self.output_format)

        if not input_path.exists():
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                success=False,
                error_message=f"Input file not found: {input_path}",
            )

        if not is_supported(input_path):
            log.warning("Extension '%s' not in known supported list — attempting anyway",
                        input_path.suffix)

        fmt = get_format_info(input_path)
        if fmt:
            log.info("Format: %s%s", fmt.name,
                     " (CAD license required)" if fmt.requires_cad_license else "")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        t_start = time.monotonic()
        try:
            asyncio.run(
                _run_conversion_async(
                    input_path=input_path,
                    output_path=output_path,
                    no_materials=no_materials,
                    single_mesh=single_mesh,
                    tessellation_chord=tessellation_chord,
                    tessellation_angle=tessellation_angle,
                    no_meter_units=no_meter_units,
                    keep_hidden=keep_hidden,
                    on_progress=on_progress,
                )
            )

            elapsed  = time.monotonic() - t_start
            out_size = output_path.stat().st_size if output_path.exists() else 0

            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                success=True,
                elapsed_seconds=elapsed,
                output_size_bytes=out_size,
            )

        except Exception as exc:
            return ConversionResult(
                input_path=input_path,
                output_path=output_path,
                success=False,
                elapsed_seconds=time.monotonic() - t_start,
                error_message=str(exc),
            )

    def shutdown(self) -> None:
        """Shut down the KitApp runtime. Call after all conversions are done."""
        shutdown_kit()
