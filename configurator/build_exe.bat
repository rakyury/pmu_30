@echo off
REM ============================================================
REM PMU-30 Configurator - Portable EXE Build Script
REM ============================================================
REM This script builds a portable executable with all dependencies
REM Requirements: Python 3.10+, pip, PyInstaller
REM ============================================================

setlocal EnableDelayedExpansion

echo ============================================================
echo PMU-30 Configurator - Build Script
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ and try again
    pause
    exit /b 1
)

REM Navigate to script directory
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Make sure PyInstaller is installed
echo.
echo Checking PyInstaller...
pip install pyinstaller>=6.0.0

REM Clean previous build
echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Build the executable
echo.
echo ============================================================
echo Building PMU-30 Configurator...
echo This may take several minutes...
echo ============================================================
echo.

pyinstaller --clean pmu_configurator.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL!
echo ============================================================
echo.
echo The portable application is located at:
echo   %CD%\dist\PMU-30_Configurator\
echo.
echo To run the application:
echo   dist\PMU-30_Configurator\PMU-30 Configurator.exe
echo.
echo You can copy the entire "PMU-30_Configurator" folder
echo to any location and run it without installation.
echo ============================================================
echo.

REM Deactivate virtual environment
deactivate

pause
