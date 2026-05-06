# This file is no longer used.
#
# The original implementation searched for a kit.exe installation on disk,
# which was needed when kit was invoked as a subprocess.
#
# kit-kernel is now installed as a pip package:
#   pip install --extra-index-url https://pypi.ngc.nvidia.com kit-kernel
#
# After pip install, 'import omni.kit.asset_converter' works directly —
# no kit.exe discovery needed.
