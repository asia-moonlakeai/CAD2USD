"""
test_modal.py — Run the CAD2USD pipeline on a real Linux/x86_64 Modal sandbox.

Usage:
    modal run test_modal.py
"""

import modal

app = modal.App("cad2usd-test")

image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.12")
    .apt_install(
        "ca-certificates",
        # Omniverse Kit Linux headless runtime dependencies
        "libxml2", "libglib2.0-0", "libsm6", "libxext6", "libxrender1",
        "libxi6", "libxtst6", "libx11-6", "libxfixes3", "libxrandr2",
        "libxcursor1", "libfontconfig1", "libfreetype6", "libgomp1",
        "libpng16-16", "binutils",
        # OpenGL stub — needed by omni.usd.libs hydra delegates even headless
        "libgl1", "libxt6",
    )
    .env({"SSL_CERT_DIR": "/etc/ssl/certs", "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt"})
    .uv_pip_install(
        "omniverse-kit",
        extra_options="--extra-index-url https://pypi.nvidia.com",
    )
    .add_local_dir("src", "/app/src")
    .add_local_dir("app", "/app/app")
    .add_local_dir("setup", "/app/setup")
)

MINIMAL_STL = """\
solid cube
  facet normal  0  0 -1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 1 0
    endloop
  endfacet
  facet normal  0  0 -1
    outer loop
      vertex 0 0 0
      vertex 1 1 0
      vertex 0 1 0
    endloop
  endfacet
  facet normal  0  0  1
    outer loop
      vertex 0 0 1
      vertex 1 1 1
      vertex 1 0 1
    endloop
  endfacet
  facet normal  0  0  1
    outer loop
      vertex 0 0 1
      vertex 0 1 1
      vertex 1 1 1
    endloop
  endfacet
endsolid cube
"""


@app.function(
    image=image,
    gpu="T4",
    timeout=600,
)
def run_conversion():
    import os
    import sys
    from pathlib import Path

    os.environ["OMNI_KIT_ACCEPT_EULA"] = "yes"
    sys.path.insert(0, "/app")

    input_path = Path("/tmp/test_cube.stl")
    output_path = Path("/tmp/test_cube.usd")
    input_path.write_text(MINIMAL_STL)

    print(f"Platform: {sys.platform}")
    print(f"Python:   {sys.version}")
    print()

    from src.converter import CadToUsdConverter, _current_platform_tag
    print(f"Platform tag: {_current_platform_tag()}")

    conv = CadToUsdConverter(verbose=True)
    result = conv.convert(input_path, output_path)
    # Check output before shutdown — shutdown can crash in headless mode
    usd_written = output_path.exists() and output_path.stat().st_size > 0
    usd_size = output_path.stat().st_size if usd_written else 0

    print()
    print(result)
    print(f"USD file written: {usd_written}  size: {usd_size:,} bytes")

    if not result.success:
        print(f"Conversion error: {result.error_message}")
        return False

    print()
    print("PASS — STL -> USD conversion succeeded on Linux/x86_64")
    # Skip conv.shutdown() — Kit shutdown can SIGSEGV in headless container
    return True


@app.local_entrypoint()
def main():
    ok = run_conversion.remote()
    if not ok:
        raise SystemExit(1)
