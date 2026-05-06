@echo off
setlocal EnableDelayedExpansion

REM =============================================================================
REM  CAD to USD Converter — Environment Validator
REM  Run after install.bat to confirm everything is set up correctly.
REM =============================================================================

title CAD to USD Converter - Validate

set REPO=%~dp0

REM --- Load config.env ---
if not exist "%REPO%config.env" (
    echo.
    echo  [ERROR] config.env not found.
    echo          Expected: %REPO%config.env
    echo          Run install.bat first.
    echo.
    exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%REPO%config.env") do (
    if not "%%A"=="" set %%A=%%B
)

if not defined PYTHON_EXE (
    echo  [ERROR] PYTHON_EXE not set in config.env. Re-run install.bat.
    exit /b 1
)
if not exist "!PYTHON_EXE!" (
    echo  [ERROR] Venv Python not found at: !PYTHON_EXE!
    echo          Re-run install.bat to rebuild the environment.
    exit /b 1
)

if not defined OMNI_KIT_ACCEPT_EULA set OMNI_KIT_ACCEPT_EULA=yes

"!PYTHON_EXE!" "%REPO%setup\validate_env.py" %*

endlocal
exit /b %ERRORLEVEL%
