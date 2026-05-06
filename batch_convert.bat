@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM  CAD to USD Converter — Batch Folder Conversion
REM
REM  Recursively scans a folder for all supported CAD files and converts them
REM  to USD, preserving the directory structure in the output folder.
REM
REM  Usage:
REM    batch_convert.bat  <input_folder>  [output_folder]  [options]
REM
REM  Options:
REM    --flat            Do not recurse into subfolders
REM    --skip-existing   Skip files whose USD output already exists
REM    --dry-run         Print what would be converted without doing it
REM    --ext EXT         Only convert files with this extension (e.g. .prt)
REM    --no-materials    Skip material/texture conversion
REM    --single-mesh     Flatten all assemblies into one mesh
REM    --fine            High quality tessellation
REM    --coarse          Fast preview tessellation
REM    --usda            Output as .usda (human-readable ASCII)
REM    --usdz            Output as .usdz package
REM    --verbose         Show detailed output per file
REM    --formats         Print all supported input formats and exit
REM
REM  Examples:
REM    batch_convert.bat  "C:\Models"  "C:\USD"
REM    batch_convert.bat  "C:\Models"  "C:\USD"  --skip-existing --fine
REM    batch_convert.bat  "C:\Models"  --ext .prt  --ext .asm
REM    batch_convert.bat  "C:\Models"  --dry-run
REM =============================================================================

title CAD to USD Converter - Batch

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

REM --- Set EULA env var ---
if not defined OMNI_KIT_ACCEPT_EULA set OMNI_KIT_ACCEPT_EULA=yes

if not defined DEFAULT_OUTPUT_FORMAT set DEFAULT_OUTPUT_FORMAT=.usd
if not defined TESSELLATION_CHORD   set TESSELLATION_CHORD=0.01
if not defined TESSELLATION_ANGLE   set TESSELLATION_ANGLE=30

REM --- Handle --formats ---
if "%~1"=="--formats" (
    "!PYTHON_EXE!" -c "import sys; sys.path.insert(0,'%REPO%'); from src.formats import print_format_table; print_format_table()"
    exit /b 0
)

if "%~1"=="" (
    echo.
    echo  Usage: batch_convert.bat ^<input_folder^> [output_folder] [options]
    echo  Run:   install.bat    to install / reinstall
    echo.
    exit /b 1
)

REM --- Parse input / output ---
set INPUT_DIR=%~1
set OUTPUT_DIR=
if not "%~2"=="" (
    set _SECOND=%~2
    if "!_SECOND:~0,2!" neq "--" (
        set OUTPUT_DIR=%~2
        shift
    )
)
shift

REM --- Collect all remaining flags ---
set PASSTHROUGH=
:parse
if "%~2"=="" goto :run
set PASSTHROUGH=!PASSTHROUGH! %~2
shift
goto :parse

:run
echo.
echo  ============================================================
echo   CAD to USD Converter — Batch Mode
echo  ============================================================
echo   Input : !INPUT_DIR!
if not "!OUTPUT_DIR!"=="" (echo   Output: !OUTPUT_DIR!) else (echo   Output: ^(next to each input file^))
echo  ============================================================
echo.

"!PYTHON_EXE!" "%REPO%run_batch.py" ^
    --input "!INPUT_DIR!" ^
    --output "!OUTPUT_DIR!" ^
    --format !DEFAULT_OUTPUT_FORMAT! ^
    --tessellation-chord !TESSELLATION_CHORD! ^
    --tessellation-angle !TESSELLATION_ANGLE! ^
    !PASSTHROUGH!

set RC=%ERRORLEVEL%
endlocal
exit /b %RC%
