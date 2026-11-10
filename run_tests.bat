@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo ============================================================================
echo   GisMarketIntelligenceAi - Test Suite Runner (Pure Pytest + pytest-mock)
echo ============================================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
set "PYTHONUTF8=1"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [INFO] Interpreter Pythona: %PYTHON_EXE%

"%PYTHON_EXE%" -c "import pytest, pytest_mock, pytest_cov, pytest_asyncio" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Doinstalowywanie brakujacych pakietow testowych ^(pytest, pytest-mock, pytest-cov, pytest-asyncio^)...
    "%PYTHON_EXE%" -m pip install pytest pytest-mock pytest-cov pytest-asyncio
    if errorlevel 1 (
        echo [ERROR] Nie udalo sie zainstalowac pakietow testowych.
        exit /b 1
    )
)

echo [INFO] Uruchamianie testow jednostkowych i integracyjnych...
echo.

if "%~1"=="" (
    "%PYTHON_EXE%" -m pytest tests -v --cov=src --cov-report=term-missing
) else (
    "%PYTHON_EXE%" -m pytest %*
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo ============================================================================
    echo   [OK] Wszystkie testy zakonczone sukcesem!
    echo ============================================================================
) else (
    echo ============================================================================
    echo   [FAIL] Wykryto bledy podczas wykonywania testow ^(kod wyjscia: %EXIT_CODE%^).
    echo ============================================================================
)

exit /b %EXIT_CODE%
