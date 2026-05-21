"""
fetch_cad_ext.py — Pre-download omni.kit.converter.cad from the NVIDIA registry.

Run once by install.bat. Starts a minimal KitApp, connects to the Kit 110
shared extension registry, and downloads omni.kit.converter.cad + its
dependencies (HOOPS Exchange translator, JT converter, DGN converter, etc.)
into Kit's local extension cache.

Subsequent runs of convert.bat / batch_convert.bat load the extension from
cache and start immediately — no network required.
"""

import asyncio
import os
import sys
import time


def _current_platform_tag() -> str:
    if sys.platform == "win32":
        return "windows-x86_64"
    if sys.platform.startswith("linux"):
        return "linux-x86_64"
    raise RuntimeError(
        f"Unsupported platform: {sys.platform}. "
        "omniverse-kit supports Windows and Linux only."
    )

os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "yes")

# Kit 110 shared registry CDN
_REG_URL = (
    "https://ovextensionsprod.blob.core.windows.net"
    "/exts/kit/prod/110/shared"
)

_TARGET_EXTS = [
    "omni.kit.converter.cad",
]


def main() -> int:
    print("  Connecting to NVIDIA extension registry...")
    print(f"  Registry: {_REG_URL}")
    print()

    try:
        from omni.kit_app import KitApp  # noqa: PLC0415
    except ImportError:
        print("  [ERROR] omniverse-kit not found. Run install.bat first.")
        return 1

    app = KitApp()

    startup_args = [
        "--/app/privacy/eula/accept=true",
        "--/app/privacy/consent/accept=true",
        "--/app/extensions/registryEnabled=true",
        f"--/app/extensions/supportedTargets/platform={_current_platform_tag()}",
        "--enable", "omni.kit.registry.nucleus",
        "--/exts/omni.kit.registry.nucleus/registries/0/name=kit/shared",
        f"--/exts/omni.kit.registry.nucleus/registries/0/url={_REG_URL}",
    ]

    for ext in _TARGET_EXTS:
        startup_args += ["--enable", ext]

    print("  Starting Kit runtime...")
    try:
        app.startup(startup_args)
    except Exception as exc:
        print(f"  [ERROR] Kit startup failed: {exc}")
        return 1

    # Give the registry time to connect and the extension time to download.
    # omni.kit.converter.cad pulls in HOOPS Exchange DLLs — allow up to 3 min.
    print("  Downloading CAD converter extension (first run only, ~2-3 min)...")
    deadline = time.monotonic() + 180
    loaded = False

    try:
        import omni.kit.app as _kit_app  # noqa: PLC0415

        def _cad_loaded(mgr) -> bool:
            """Check if the CAD extension is present — tries several Kit API shapes."""
            targets = ["omni.kit.converter.cad", "omni.kit.converter.hoops"]
            for name in targets:
                # Kit 110 uses get_enabled_extension_id()
                if hasattr(mgr, "get_enabled_extension_id"):
                    if mgr.get_enabled_extension_id(name):
                        return True
                # Older shape
                if hasattr(mgr, "is_extension_present"):
                    if mgr.is_extension_present(name):
                        return True
                # Fallback: check if the Python package is importable
                import importlib
                try:
                    importlib.import_module(name.replace(".", "_"))
                    return True
                except ImportError:
                    pass
            # Last resort: check sys.modules for any omni.kit.converter submodule
            return any(
                k.startswith("omni.kit.converter") for k in sys.modules
            )

        while time.monotonic() < deadline:
            mgr = _kit_app.get_app().get_extension_manager()
            if _cad_loaded(mgr):
                loaded = True
                break
            _kit_app.get_app().update()
            time.sleep(1)
            sys.stdout.write(".")
            sys.stdout.flush()

    except Exception as exc:
        print(f"\n  [WARN] Could not check extension status: {exc}")

    print()
    if loaded:
        print("  [OK]  omni.kit.converter.cad downloaded and cached")
        print("        CAD formats (Creo, CATIA, NX, SolidWorks, etc.) are now enabled.")
    else:
        print("  [WARN] Extension may not have finished downloading within the timeout.")
        print("         Try running convert.bat — it will retry automatically.")
        print("         Or check your network access to:")
        print(f"         {_REG_URL}")

    try:
        app.shutdown()
    except Exception:
        pass

    return 0 if loaded else 1


if __name__ == "__main__":
    sys.exit(main())
