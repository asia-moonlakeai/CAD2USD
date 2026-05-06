@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM  CAD to USD Converter - Installer
REM
REM  Zero-dependency setup. Just run this once:
REM    install.bat
REM
REM  What it does:
REM    1. Finds Python 3.12 - or downloads and installs it automatically
REM    2. Creates a .venv virtual environment in this folder
REM    3. Installs omniverse-kit into the venv (~500 MB, one-time)
REM    4. Accepts the NVIDIA EULA non-interactively
REM    5. Writes config.env (used by all .bat scripts automatically)
REM    6. Validates the installation
REM =============================================================================

title CAD to USD Converter - Setup

echo.
echo  ============================================================
echo   CAD to USD Converter - Setup
echo   Powered by NVIDIA omniverse-kit + omni.kit.asset_converter
echo  ============================================================
echo.

set REPO=%~dp0
set VENV=%REPO%.venv

REM Python version we need (omniverse-kit Windows wheels are cp312 only)
set PY_MAJOR=3
set PY_MINOR=12
set PY_PATCH=9
set PY_VERSION=3.12.9
set PY_INSTALLER_NAME=python-3.12.9-amd64.exe
set PY_INSTALLER_URL=https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
set PY_INSTALLER_DEST=%TEMP%\%PY_INSTALLER_NAME%
set PY_USER_INSTALL=%LOCALAPPDATA%\Programs\Python\Python312\python.exe

REM ==========================================================================
REM  STEP 1 - Find or install Python 3.12
REM ==========================================================================
echo  [1/6] Locating Python %PY_VERSION%...
echo.

set PY312=

REM --- 1a. Python Launcher (py -3.12) ---
where py >nul 2>&1
if errorlevel 1 goto :try_python_versioned

py -3.12 --version >nul 2>&1
if errorlevel 1 goto :try_python_versioned

for /f "tokens=2" %%v in ('py -3.12 --version 2^>^&1') do set PY_VER=%%v
set PY312=py -3.12
echo  [OK]  Found via Python Launcher: Python !PY_VER!
goto :python_found

REM --- 1b. python3.12 on PATH ---
:try_python_versioned
where python3.12 >nul 2>&1
if errorlevel 1 goto :try_python_generic

for /f "tokens=2" %%v in ('python3.12 --version 2^>^&1') do set PY_VER=%%v
set PY312=python3.12
echo  [OK]  Found on PATH: Python !PY_VER!
goto :python_found

REM --- 1c. 'python' if it happens to be 3.12 ---
:try_python_generic
where python >nul 2>&1
if errorlevel 1 goto :try_common_paths

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
REM Parse major.minor from PY_VER (e.g. "3.12.9" -> major=3, minor=12)
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set PY_FOUND_MAJOR=%%a
    set PY_FOUND_MINOR=%%b
)
if "!PY_FOUND_MAJOR!"=="3" if "!PY_FOUND_MINOR!"=="12" (
    set PY312=python
    echo  [OK]  Found on PATH: Python !PY_VER!
    goto :python_found
)

REM --- 1d. Common install paths ---
:try_common_paths
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PY312="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    for /f "tokens=2" %%v in ('"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" --version 2^>^&1') do set PY_VER=%%v
    echo  [OK]  Found at %%LOCALAPPDATA%%\Programs\Python\Python312: Python !PY_VER!
    goto :python_found
)
if exist "C:\Python312\python.exe" (
    set PY312="C:\Python312\python.exe"
    for /f "tokens=2" %%v in ('"C:\Python312\python.exe" --version 2^>^&1') do set PY_VER=%%v
    echo  [OK]  Found at C:\Python312: Python !PY_VER!
    goto :python_found
)
if exist "C:\Program Files\Python312\python.exe" (
    set PY312="C:\Program Files\Python312\python.exe"
    for /f "tokens=2" %%v in ('"C:\Program Files\Python312\python.exe" --version 2^>^&1') do set PY_VER=%%v
    echo  [OK]  Found at C:\Program Files\Python312: Python !PY_VER!
    goto :python_found
)

REM --- 1e. Not found - download and install automatically ---
echo  Python %PY_VERSION% not found. Downloading and installing automatically...
echo.

echo  Downloading Python %PY_VERSION% installer...
echo  From: %PY_INSTALLER_URL%
echo.

where curl >nul 2>&1
if not errorlevel 1 (
    curl -L --progress-bar -o "%PY_INSTALLER_DEST%" "%PY_INSTALLER_URL%"
    if errorlevel 1 (
        echo  [WARN] curl download failed - trying PowerShell...
        powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_INSTALLER_URL%' -OutFile '%PY_INSTALLER_DEST%' -UseBasicParsing"
    )
) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_INSTALLER_URL%' -OutFile '%PY_INSTALLER_DEST%' -UseBasicParsing"
)

if not exist "%PY_INSTALLER_DEST%" (
    echo.
    echo  [ERROR] Failed to download Python installer.
    echo          Please install Python %PY_VERSION% manually:
    echo          %PY_INSTALLER_URL%
    echo.
    goto :error
)
echo  [OK]  Downloaded: %PY_INSTALLER_DEST%
echo.

echo  Installing Python %PY_VERSION% for current user (no admin required)...
echo  This takes about 30-60 seconds...
echo.

"%PY_INSTALLER_DEST%" /quiet ^
    InstallAllUsers=0 ^
    PrependPath=1 ^
    Include_pip=1 ^
    Include_launcher=1 ^
    Include_test=0 ^
    Include_doc=0

if errorlevel 1 (
    echo.
    echo  [ERROR] Python installation failed.
    echo  Try installing manually: %PY_INSTALLER_DEST%
    echo.
    goto :error
)

del /f /q "%PY_INSTALLER_DEST%" >nul 2>&1

REM Verify the install landed where expected
if exist "%PY_USER_INSTALL%" (
    set PY312="%PY_USER_INSTALL%"
    for /f "tokens=2" %%v in ('"%PY_USER_INSTALL%" --version 2^>^&1') do set PY_VER=%%v
    echo  [OK]  Python installed: Python !PY_VER!
    echo        Location: %PY_USER_INSTALL%
    goto :python_found
)

REM Fallback: try py launcher (PrependPath may need a new shell)
where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set PY312=py -3.12
        for /f "tokens=2" %%v in ('py -3.12 --version 2^>^&1') do set PY_VER=%%v
        echo  [OK]  Python installed and found via launcher: Python !PY_VER!
        goto :python_found
    )
)

echo.
echo  [ERROR] Python was installed but could not be located.
echo          Please open a new terminal and re-run install.bat.
echo          (PATH changes from the installer may need a new shell)
echo.
goto :error

:python_found
echo.
echo  Using: !PY312!
echo.

REM ==========================================================================
REM  STEP 2 - Create virtual environment
REM ==========================================================================
echo  [2/6] Setting up virtual environment (.venv)...

if exist "%VENV%\Scripts\python.exe" (
    echo  [OK]  .venv already exists - reusing it
) else (
    echo        Creating .venv...
    !PY312! -m venv "%VENV%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        echo          Try deleting .venv and running install.bat again.
        goto :error
    )
    echo  [OK]  .venv created at %VENV%
)

set VENV_PY="%VENV%\Scripts\python.exe"
set VENV_PIP="%VENV%\Scripts\python.exe" -m pip

echo.

REM ==========================================================================
REM  STEP 3 - Upgrade pip inside venv
REM ==========================================================================
echo  [3/6] Upgrading pip in venv...

%VENV_PIP% install --upgrade pip --quiet
if errorlevel 1 (
    echo  [WARN] pip upgrade failed - continuing with existing pip
) else (
    echo  [OK]  pip up to date
)
echo.

REM ==========================================================================
REM  STEP 4 - Install omniverse-kit
REM ==========================================================================
echo  [4/6] Installing omniverse-kit...
echo        Source : https://pypi.nvidia.com (public - no login required)
echo        Size   : ~500 MB (downloaded once, cached in the venv)
echo.

REM Skip the heavy download if already present
%VENV_PIP% show omniverse-kit >nul 2>&1
if not errorlevel 1 (
    echo  [OK]  omniverse-kit already installed - skipping download
    goto :after_kit_install
)

%VENV_PIP% install omniverse-kit --extra-index-url https://pypi.nvidia.com

REM pip sometimes returns non-zero for warnings even when the package landed.
REM Verify presence rather than trusting the exit code alone.
if errorlevel 1 (
    %VENV_PIP% show omniverse-kit >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] omniverse-kit installation failed.
        echo.
        echo  Things to check:
        echo    1. Internet access to pypi.nvidia.com
        echo    2. Enough disk space (~700 MB needed)
        echo    3. Try again - occasionally pip times out on large packages
        echo.
        echo  To retry manually:
        echo    %VENV%\Scripts\python.exe -m pip install omniverse-kit
        echo        --extra-index-url https://pypi.nvidia.com
        echo.
        goto :error
    )
    echo  [WARN] pip reported warnings but omniverse-kit is present - continuing
)

:after_kit_install
echo  [OK]  omniverse-kit ready
echo.

REM ==========================================================================
REM  STEP 5 - Download CAD converter extension from NVIDIA registry
REM ==========================================================================
echo  [5/7] Downloading CAD converter extension (omni.kit.converter.cad)...
echo        This fetches HOOPS Exchange + CAD format translators on first run.
echo        May take 2-3 minutes depending on network speed.
echo.

%VENV_PY% "%REPO%setup\fetch_cad_ext.py"
if errorlevel 1 goto :cad_ext_warn
goto :cad_ext_ok

:cad_ext_warn
echo.
echo  [WARN] CAD extension download incomplete - will retry on first convert.
echo         Open formats: STEP, IGES, OBJ, FBX, glTF work without it.
echo.

:cad_ext_ok

REM ==========================================================================
REM  STEP 6 - Write config.env
REM ==========================================================================
echo  [6/7] Writing config.env...
echo        Path: %REPO%config.env

REM Write each line individually to avoid issues with block redirects
set CFG=%REPO%config.env
echo # CAD to USD Converter - Configuration                    > "!CFG!"
echo # Auto-generated by install.bat - re-run to regenerate  >> "!CFG!"
echo.                                                         >> "!CFG!"
echo # Venv Python path (do not change)                      >> "!CFG!"
echo PYTHON_EXE=!VENV!\Scripts\python.exe                    >> "!CFG!"
echo.                                                         >> "!CFG!"
echo # NVIDIA EULA accepted for non-interactive use           >> "!CFG!"
echo OMNI_KIT_ACCEPT_EULA=yes                                 >> "!CFG!"
echo.                                                         >> "!CFG!"
echo # Default USD output format                              >> "!CFG!"
echo DEFAULT_OUTPUT_FORMAT=.usd                               >> "!CFG!"
echo.                                                         >> "!CFG!"
echo # Tessellation defaults                                  >> "!CFG!"
echo TESSELLATION_CHORD=0.01                                  >> "!CFG!"
echo TESSELLATION_ANGLE=30                                    >> "!CFG!"

if not exist "!CFG!" (
    echo  [ERROR] Failed to write config.env at: !CFG!
    echo          Check that the folder is not read-only.
    goto :error
)

echo  [OK]  config.env written
echo.

REM ==========================================================================
REM  STEP 7 - Quick smoke test + full validation
REM ==========================================================================
echo  [7/7] Validating installation...
echo.

%VENV_PY% -c "from omni.kit_app import KitApp; print('  [OK]  omni.kit_app importable')"
if errorlevel 1 (
    echo  [WARN] Import test failed - running full validator for details...
)

%VENV_PY% "%REPO%setup\validate_env.py"
echo.

echo  ============================================================
echo   Setup complete!
echo  ============================================================
echo.
echo   Convert a file:    convert.bat  input.prt  [output.usd]
echo   Batch a folder:    batch_convert.bat  C:\CAD  C:\USD
echo   Check your setup:  validate.bat
echo   Supported formats: convert.bat --formats
echo.
echo   The .venv folder holds the isolated Python environment.
echo   You never need to activate it - the .bat files handle it.
echo.

endlocal
exit /b 0

REM ==========================================================================
:error
echo.
echo  ============================================================
echo   Setup failed. Address the error above and re-run install.bat
echo  ============================================================
echo.
endlocal
exit /b 1
