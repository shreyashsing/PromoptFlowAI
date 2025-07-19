@echo off
REM Windows setup script for PromptFlow AI Backend

echo 🚀 Setting up PromptFlow AI Backend Environment (Windows)
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created successfully!
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment and install dependencies
echo 📦 Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
if exist "requirements.txt" (
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed successfully!
) else (
    echo ⚠️  requirements.txt not found
)

echo.
echo 🎉 Setup complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and configure your settings
echo 2. Run database initialization: python scripts\init_db.py
echo 3. Start the server: uvicorn app.main:app --reload
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
pause