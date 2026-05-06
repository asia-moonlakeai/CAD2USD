"""
Supported CAD and 3D formats for omni.kit.asset_converter.

All formats listed here are supported by the NVIDIA Omniverse CAD Converter
extension (omni.kit.asset_converter). Formats marked as requiring a CAD
Converter license need the licensed extension pack — available via NVIDIA
Omniverse Enterprise or through your NVIDIA account.

Reference:
  https://docs.omniverse.nvidia.com/extensions/latest/ext_asset-converter.html
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set


@dataclass
class FormatInfo:
    name: str
    extensions: Set[str]
    description: str
    requires_cad_license: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------

FORMATS: list[FormatInfo] = [
    # --- Native CAD (require CAD Converter license) ---
    FormatInfo(
        name="PTC Creo / Pro/Engineer",
        extensions={".prt", ".asm", ".xpr", ".xas", ".g", ".neu"},
        description="PTC Creo Parametric parts and assemblies",
        requires_cad_license=True,
    ),
    FormatInfo(
        name="CATIA V5 / V6",
        extensions={".catpart", ".catproduct", ".cgr", ".3dxml"},
        description="Dassault Systèmes CATIA parts and products",
        requires_cad_license=True,
    ),
    FormatInfo(
        name="Siemens NX",
        extensions={".prt"},  # NX .prt — different from Creo, detected by content
        description="Siemens NX / Unigraphics parts and assemblies",
        requires_cad_license=True,
        notes="NX .prt files share the extension with Creo; converter disambiguates by file header.",
    ),
    FormatInfo(
        name="SolidWorks",
        extensions={".sldprt", ".sldasm", ".slddrw"},
        description="Dassault Systèmes SolidWorks parts and assemblies",
        requires_cad_license=True,
    ),
    FormatInfo(
        name="Autodesk Inventor",
        extensions={".ipt", ".iam", ".ipn"},
        description="Autodesk Inventor parts, assemblies, and presentations",
        requires_cad_license=True,
    ),
    FormatInfo(
        name="Solid Edge",
        extensions={".par", ".asm", ".psm"},
        description="Siemens Solid Edge parts and assemblies",
        requires_cad_license=True,
    ),
    FormatInfo(
        name="JT (Jupiter Tessellation)",
        extensions={".jt"},
        description="Siemens JT lightweight 3D format",
        requires_cad_license=True,
    ),

    # --- Open / neutral formats (no CAD license required) ---
    FormatInfo(
        name="STEP",
        extensions={".stp", ".step"},
        description="ISO 10303 Standard for the Exchange of Product Data (AP203, AP214, AP242)",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="IGES",
        extensions={".igs", ".iges"},
        description="Initial Graphics Exchange Specification",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="Parasolid",
        extensions={".x_t", ".x_b", ".xmt_txt", ".xmt_bin"},
        description="Siemens Parasolid kernel format (text and binary)",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="ACIS / SAT",
        extensions={".sat", ".sab"},
        description="Spatial ACIS kernel format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="Rhino 3DM",
        extensions={".3dm"},
        description="McNeel Rhinoceros 3D model format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="OBJ",
        extensions={".obj"},
        description="Wavefront OBJ mesh format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="FBX",
        extensions={".fbx"},
        description="Autodesk FBX interchange format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="glTF / GLB",
        extensions={".gltf", ".glb"},
        description="Khronos Group glTF 2.0 format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="STL",
        extensions={".stl"},
        description="Stereolithography tessellation format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="Collada",
        extensions={".dae"},
        description="COLLADA digital asset exchange format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="DXF",
        extensions={".dxf"},
        description="AutoCAD Drawing Exchange Format",
        requires_cad_license=False,
    ),
    FormatInfo(
        name="USD (input)",
        extensions={".usd", ".usda", ".usdc", ".usdz"},
        description="Universal Scene Description (as input — e.g. for reprocessing)",
        requires_cad_license=False,
    ),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _build_extension_map() -> dict[str, FormatInfo]:
    """Build a flat dict of extension -> FormatInfo for fast lookups."""
    ext_map: dict[str, FormatInfo] = {}
    for fmt in FORMATS:
        for ext in fmt.extensions:
            ext_map[ext.lower()] = fmt
    return ext_map


_EXT_MAP: dict[str, FormatInfo] = _build_extension_map()

# All extensions as a flat set (lowercase, with leading dot)
ALL_SUPPORTED_EXTENSIONS: Set[str] = set(_EXT_MAP.keys())


def real_suffix(path: str | Path) -> str:
    """
    Return the meaningful CAD file extension, stripping Creo version suffixes.

    Creo appends an integer version number on every save, e.g.:
        wheel.prt.1   ->  .prt
        engine.asm.12 ->  .asm
        part.stp      ->  .stp   (unchanged)
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix.lstrip(".").isdigit():
        return Path(p.stem).suffix.lower()
    return suffix


def get_format_info(path: str | Path) -> FormatInfo | None:
    """Return the FormatInfo for a file, or None if unsupported."""
    return _EXT_MAP.get(real_suffix(path))


def is_supported(path: str | Path) -> bool:
    """Return True if the file extension is supported by the converter."""
    return real_suffix(path) in _EXT_MAP


def requires_cad_license(path: str | Path) -> bool:
    """Return True if this format needs the CAD Converter license pack."""
    info = get_format_info(path)
    return info.requires_cad_license if info else False


def print_format_table() -> None:
    """Print a human-readable table of all supported formats."""
    print(f"\n{'Format':<30} {'Extensions':<35} {'License'}")
    print("-" * 75)
    for fmt in FORMATS:
        exts = ", ".join(sorted(fmt.extensions))
        license_tag = "CAD License" if fmt.requires_cad_license else "Included"
        print(f"{fmt.name:<30} {exts:<35} {license_tag}")
    print()
