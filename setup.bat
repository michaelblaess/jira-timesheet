@echo off
echo === Jira Timesheet Setup ===
echo.

python -m venv "%~dp0.venv"

REM SSL-Workaround: pip.ini fuer ALLE pip-Aufrufe (auch Build-Subprocesses)
set PIP_TRUSTED=--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
if not exist "%~dp0.venv\pip.ini" (
    echo [global]> "%~dp0.venv\pip.ini"
    echo trusted-host = pypi.org pypi.python.org files.pythonhosted.org>> "%~dp0.venv\pip.ini"
)

echo Installiere Dependencies...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet %PIP_TRUSTED%
"%~dp0.venv\Scripts\pip.exe" install -e "%~dp0." --quiet %PIP_TRUSTED%

echo Aktualisiere textual-themes (Git-Dependency)...
"%~dp0.venv\Scripts\pip.exe" install --force-reinstall --no-deps --quiet %PIP_TRUSTED% "textual-themes @ git+https://github.com/michaelblaess/textual-themes.git"

echo.
echo === Setup abgeschlossen ===
echo Starte mit: run.bat
pause
