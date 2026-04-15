@echo off
setlocal enabledelayedexpansion

REM This Source Code Form is subject to the terms of the Mozilla Public
REM License, v. 2.0. If a copy of the MPL was not distributed with this
REM file, You can obtain one at https://mozilla.org/MPL/2.0/.
REM
REM This software was developed and implemented by MDSight, LLC
REM with project management by Lieberthal & Associates, LLC
REM and funding from the Casualty Actuarial Society.

REM ================================================================================
REM LLM Claims Analysis Pipeline - Run Script (Windows)
REM
REM This script starts the development servers:
REM 1. Detects and activates the virtual environment
REM 2. Starts Flask backend server (port 5000)
REM 3. Starts Vite frontend dev server (port 3000)
REM ================================================================================

echo.
echo ================================
echo LLM Claims Analysis - Starting
echo ================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [i] Script directory: %SCRIPT_DIR%
echo.

REM ================================================================================
REM VENV DETECTION LOGIC
REM ================================================================================

echo [*] Detecting virtual environment...
echo.

REM Configure Analytics venv location (edit this path if different)
set "ANALYTICS_VENV=\path_to_environment\.venv"

REM Priority 1: Already activated venv
if defined VIRTUAL_ENV (
    set "VENV_DIR=%VIRTUAL_ENV%"
    echo [+] Using already activated venv: !VENV_DIR!
    set "VENV_ALREADY_ACTIVE=true"
    goto venv_detected
)

REM Priority 2: Environment variable override
if defined LLM_VENV_PATH (
    set "VENV_DIR=%LLM_VENV_PATH%"
    echo [+] Using venv from LLM_VENV_PATH: !VENV_DIR!
    set "VENV_ALREADY_ACTIVE=false"
    goto venv_detected
)

REM Priority 3: Analytics venv exists
if exist "%ANALYTICS_VENV%\Scripts\python.exe" (
    set "VENV_DIR=%ANALYTICS_VENV%"
    echo [+] Found Analytics venv: !VENV_DIR!
    set "VENV_ALREADY_ACTIVE=false"
    goto venv_detected
)

REM Priority 4: Local venv
set "VENV_DIR=%SCRIPT_DIR%.venv"
echo [i] Using local venv: !VENV_DIR!
set "VENV_ALREADY_ACTIVE=false"

:venv_detected

REM ================================================================================
REM END VENV DETECTION LOGIC
REM ================================================================================

REM Check if venv exists
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment not found at: %VENV_DIR%
    echo.
    echo Please run setup first:
    echo   setup.bat
    echo.
    pause
    exit /b 1
)

REM Activate the virtual environment if not already active
if "%VENV_ALREADY_ACTIVE%"=="false" (
    if exist "%VENV_DIR%\Scripts\activate.bat" (
        call "%VENV_DIR%\Scripts\activate.bat"
        echo [+] Virtual environment activated
    ) else (
        echo [ERROR] Cannot find activation script in venv
        pause
        exit /b 1
    )
) else (
    echo [i] Virtual environment already activated
)

echo.

REM ================================================================================
REM Kill any existing processes on ports 3000 and 5000
REM ================================================================================

echo [*] Checking for existing processes on ports 3000 and 5000...

REM Kill processes on port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill processes on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do (
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 1 >nul
echo [+] Ports cleared
echo.

REM ================================================================================
REM Start servers
REM ================================================================================

echo.
echo ================================
echo Starting Servers
echo ================================
echo.
echo [*] Frontend (dev): http://localhost:3000
echo [*] Backend API:    http://localhost:5000/api
echo.
echo Hot reload enabled on frontend
echo ================================
echo.

REM Check if backend exists
if not exist "app\backend\app.py" (
    echo [ERROR] Backend not found at: app\backend\app.py
    echo.
    echo Please ensure you're in the correct directory and setup was completed.
    pause
    exit /b 1
)

REM Check if frontend exists
if not exist "app\frontend" (
    echo [ERROR] Frontend not found at: app\frontend\
    echo.
    echo Please ensure you're in the correct directory and setup was completed.
    pause
    exit /b 1
)

REM Start backend in a new window
echo [*] Starting Flask backend...
start "Flask Backend" /MIN python app\backend\app.py

REM Give backend time to start
timeout /t 3 >nul
echo [+] Backend started
echo.

REM Start frontend dev server
echo [*] Starting Vite dev server...
echo.

cd app\frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo [ERROR] Frontend dependencies not installed
    echo.
    echo Please run setup first
    pause
    exit /b 1
)

REM Run npm dev (this will run in current window)
call npm run dev

REM When npm exits, window will close
echo.
pause
