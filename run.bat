@echo off
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m jira_timesheet %*
) else (
    python -m jira_timesheet %*
)
