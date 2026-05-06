@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM  CAD to USD Converter — Single File
REM
REM  Usage:
REM    convert.bat  <input_file>  [output_file]  [options]
REM
REM  Options:
REM    --fine           High quality tessellation (chord=0.001, angle=10°)
REM    --coarse         Fast preview tessellation (chord=0.1, angle=45°)
REM    --no-materials   Skip material/texture conversion
REM    --single-mesh    Flatten assembly into one mesh
REM    --usda           Output as .usda (human-readable ASCII)
REM    --usdz           Output as .usdz (zip package, for AR/mobile)
REM    --verbose        Verbose output
REM    --formats        List all supported formats and exit
REM
REM  Examples:
REM    convert.bat  "wheel.prt"
REM    convert.bat  "assembly.asm"  "C:\USD\assembly.usd"
REM    convert.bat  "part.stp"  --fine  --no-materials
REM =============================================================================

title CAD to USD Converter

set REPO=%~dp0

REM --- Load config.env ---
if not exist "%REPO%config.env" (
    echo.
    echo  [ERROR] config.env not found. Run install.bat first.
    echo.
    exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%REPO%config.env") do (
    if not "%%A"=="" set %%A=%%B
)

REM --- Resolve Python from venv ---
if not defined PYTHON_EXE (
    echo  [ERROR] PYTHON_EXE not set in config.env. Re-run install.bat.
    exit /b 1
)
if not exist "!PYTHON_EXE!" (
    echo  [ERROR] Venv Python not found at: !PYTHON_EXE!
    echo          Re-run install.bat to rebuild the environment.
    exit /b 1
)

REM --- Set EULA env var (required for omniverse-kit to start non-interactively) ---
if defined OMNI_KIT_ACCEPT_EULA set OMNI_KIT_ACCEPT_EULA=!OMNI_KIT_ACCEPT_EULA!
if not defined OMNI_KIT_ACCEPT_EULA set OMNI_KIT_ACCEPT_EULA=yes

if not defined DEFAULT_OUTPUT_FORMAT set DEFAULT_OUTPUT_FORMAT=.usd

REM --- Handle --formats flag ---
if "%~1"=="--formats" (
    "!PYTHON_EXE!" -c "import sys; sys.path.insert(0,'%REPO%'); from src.formats import print_format_table; print_format_table()"
    exit /b 0
)

REM --- Require at least one argument ---
if "%~1"=="" (
    echo.
    echo  Usage: convert.bat ^<input_file^> [output_file] [options]
    echo  Run:   convert.bat --formats   to list supported formats
    echo         install.bat             to install / reinstall
    echo.
    exit /b 1
)

REM --- Parse input / output ---
set INPUT_FILE=%~1
set OUTPUT_FILE=
if not "%~2"=="" (
    set _SECOND=%~2
    if "!_SECOND:~0,2!" neq "--" (
        set OUTPUT_FILE=%~2
        shift
    )
)
shift

REM --- Collect remaining flags ---
set PASSTHROUGH=
:parse
if "%~2"=="" goto :run
set PASSTHROUGH=!PASSTHROUGH! %~2
shift
goto :parse

:run
set OUT_ARG=
if not "!OUTPUT_FILE!"=="" set OUT_ARG=--output "!OUTPUT_FILE!"

"!PYTHON_EXE!" "%REPO%app\run_conversion.py" ^
    --input "!INPUT_FILE!" ^
    !OUT_ARG! ^
    --format !DEFAULT_OUTPUT_FORMAT! ^
    !PASSTHROUGH!

set RC=%ERRORLEVEL%
endlocal
exit /b %RC%
