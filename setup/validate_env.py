"""
validate_env.py — Verify the kit-kernel environment is correctly set up.

Run after install.bat:
    python setup\validate_env.py
Or via:
    validate.bat
"""

import os
import sys
from pathlib import Path

PASS = "  [OK]  "
WARN = "  [WARN]"
FAIL = "  [FAIL]"


def _check(label: str, ok: bool, message: str = "", warn_only: bool = False) -> bool:
    tag = PASS if ok else (WARN if warn_only else FAIL)
    print(f"{tag} {label}")
    if message and not ok:
        for line in message.strip().splitlines():
            print(f"         {line}")
    return ok


def validate() -> bool:
    print()
    print("=" * 62)
    print("  CAD to USD Converter — Environment Check")
    print("=" * 62)
    print()

    all_ok = True

    # 1. Python version — Windows wheels are cp312 only, no exceptions
    major, minor = sys.version_info[:2]
    ok = major == 3 and minor == 12
    _check(
        f"Python {major}.{minor}",
        ok,
        f"omniverse-kit Windows wheels are cp312 only. Current: {major}.{minor}\n"
        "Download Python 3.12: https://python.org/downloads/release/python-3120/",
    )
    all_ok &= ok

    # 2. omniverse-kit installed — check via omni.kit_app (the correct entry point)
    # IMPORTANT: omni.kit_app must be the FIRST omniverse import
    try:
        from omni.kit_app import KitApp  # noqa: F401
        _check("omniverse-kit (omni.kit_app)", True)
    except ImportError:
        _check(
            "omniverse-kit",
            False,
            "Install: pip install omniverse-kit --extra-index-url https://pypi.nvidia.com",
        )
        all_ok = False

    # 3. Start KitApp and enable asset converter
    kit_app_instance = None
    try:
        os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "yes")
        from omni.kit_app import KitApp  # noqa: F401,F811
        kit_app_instance = KitApp()
        kit_app_instance.startup(["--enable", "omni.kit.asset_converter"])
        _check("KitApp starts + omni.kit.asset_converter enabled", True)
    except Exception as exc:
        _check("KitApp starts + omni.kit.asset_converter enabled", False, str(exc))
        all_ok = False

    # 4. omni.kit.asset_converter importable after startup
    if kit_app_instance:
        try:
            import omni.kit.asset_converter  # noqa: F401
            _check("omni.kit.asset_converter importable", True)
        except ImportError as exc:
            _check("omni.kit.asset_converter importable", False, str(exc))
            all_ok = False

    # 5. EULA acceptance
    eula_accepted = os.environ.get("OMNI_KIT_ACCEPT_EULA", "").lower() in ("yes", "1", "true")
    _check(
        "OMNI_KIT_ACCEPT_EULA set",
        eula_accepted,
        warn_only=True,
        message="Set OMNI_KIT_ACCEPT_EULA=yes to skip the interactive EULA prompt.",
    )

    # 6. CAD Converter license extension
    print()
    print("  Checking CAD Converter license extension...")
    if kit_app_instance:
        try:
            import omni.kit.app as omni_kit_app  # noqa: F401
            mgr = omni_kit_app.get_app().get_extension_manager()
            cad_exts = [
                "omni.kit.converter.cad",
                "omni.kit.converter.hoops",
            ]
            cad_found = any(mgr.is_extension_present(e) for e in cad_exts)
            if cad_found:
                print(f"{PASS} CAD converter extension loaded (omni.kit.converter.cad)")
            else:
                print(f"{WARN} omni.kit.converter.cad not loaded")
                print("         On first run Kit downloads it from the extension registry.")
                print("         Try running convert.bat on a file — it triggers the download.")
                print("         STEP, IGES, OBJ, FBX, glTF work without it.")
        except Exception:
            print(f"{WARN} Could not check CAD extension")
    else:
        print(f"{WARN} Skipped — KitApp did not start successfully")

    # Shutdown the test KitApp
    if kit_app_instance:
        try:
            kit_app_instance.shutdown()
        except Exception:
            pass

    # 7. Project structure
    print()
    print("  Checking project files...")
    repo_root = Path(__file__).parent.parent
    files_to_check = [
        ("app/run_conversion.py", True),
        ("app/cad_converter.kit", True),
        ("src/converter.py",       True),
        ("src/batch.py",           True),
        ("src/formats.py",         True),
        ("config.env",             False),  # warn only — created by install.bat
    ]
    for rel_path, required in files_to_check:
        p = repo_root / rel_path
        exists = p.exists()
        if required:
            ok = _check(rel_path, exists,
                        f"File missing — re-clone or re-run install.bat")
            all_ok &= ok
        else:
            _check(rel_path, exists, warn_only=True,
                   message="Not found — run install.bat to create it")

    # Summary
    print()
    print("=" * 62)
    if all_ok:
        print("  All checks passed — ready to convert!")
        print()
        print("  convert.bat  input.prt  output.usd")
    else:
        print("  Some checks failed — run install.bat to fix them.")
    print("=" * 62)
    print()

    return all_ok


if __name__ == "__main__":
    ok = validate()
    sys.exit(0 if ok else 1)
