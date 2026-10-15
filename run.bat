:: run.bat

@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo AI JobMatch Agent - Setup and Launch
echo ==========================================

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
)

set "PY=%CD%\.venv\Scripts\python.exe"

echo ------------------------------------------
echo Checking Python environment...
echo ------------------------------------------
"%PY%" --version
if errorlevel 1 (
    echo [ERROR] Python environment is not working.
    pause
    exit /b 1
)

echo ------------------------------------------
echo Upgrading pip...
echo ------------------------------------------
"%PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause
    exit /b 1
)

echo ------------------------------------------
echo Installing application and dependencies...
echo ------------------------------------------
"%PY%" -m pip install -e ".[dev]"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo Check pyproject.toml and the installation output.
    pause
    exit /b 1
)

echo ------------------------------------------
echo Verifying required packages...
echo ------------------------------------------
"%PY%" -c "import streamlit, pytest, pydantic, requests, langgraph"
if errorlevel 1 (
    echo [ERROR] A required package is missing.
    pause
    exit /b 1
)

echo ------------------------------------------
echo Running automated tests...
echo ------------------------------------------
"%PY%" -m pytest tests -v
if errorlevel 1 (
    echo [WARNING] Tests failed. Review the output before proceeding.
    choice /M "Launch dashboard anyway"
    if errorlevel 2 exit /b 1
)

echo ------------------------------------------
echo Launching AI JobMatch Agent...
echo ------------------------------------------
"%PY%" -m streamlit run app.py

set "EXIT_CODE=%ERRORLEVEL%"
echo ------------------------------------------
echo AI JobMatch Agent has stopped.
echo ------------------------------------------
endlocal & exit /b %EXIT_CODE%